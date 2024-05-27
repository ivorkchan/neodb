from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import BadRequest, ObjectDoesNotExist, PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from catalog.models import Item
from common.utils import AuthedHttpRequest, get_uuid_or_404
from mastodon.api import boost_toot_later, share_collection

from ..forms import *
from ..models import *
from .common import render_relogin, target_identity_required


@login_required
def add_to_collection(request: AuthedHttpRequest, item_uuid):
    item = get_object_or_404(Item, uid=get_uuid_or_404(item_uuid))
    if request.method == "GET":
        collections = Collection.objects.filter(owner=request.user.identity)
        return render(
            request,
            "add_to_collection.html",
            {
                "item": item,
                "collections": collections,
            },
        )
    else:
        cid = int(request.POST.get("collection_id", default=0))
        if not cid:
            cid = Collection.objects.create(
                owner=request.user.identity,
                title=_("Collection by {0}").format(request.user.display_name),
            ).pk
        collection = Collection.objects.get(owner=request.user.identity, id=cid)
        collection.append_item(item, note=request.POST.get("note"))
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


def collection_retrieve_redirect(request: AuthedHttpRequest, collection_uuid):
    return redirect(f"/collection/{collection_uuid}", permanent=True)


def collection_retrieve(request: AuthedHttpRequest, collection_uuid):
    collection = get_object_or_404(Collection, uid=get_uuid_or_404(collection_uuid))
    if not collection.is_visible_to(request.user):
        raise PermissionDenied(_("Insufficient permission"))
    follower_count = collection.likes.all().count()
    following = (
        Like.user_liked_piece(request.user.identity, collection)
        if request.user.is_authenticated
        else False
    )
    featured_since = (
        collection.featured_since(request.user.identity)
        if request.user.is_authenticated
        else None
    )
    available_as_featured = (
        request.user.is_authenticated
        and (following or request.user.identity == collection.owner)
        and not featured_since
        and collection.members.all().exists()
    )
    stats = {}
    if featured_since:
        stats = collection.get_stats(request.user.identity)
        stats["wishlist_deg"] = (
            round(stats["wishlist"] / stats["total"] * 360) if stats["total"] else 0
        )
        stats["progress_deg"] = (
            round(stats["progress"] / stats["total"] * 360) if stats["total"] else 0
        )
        stats["complete_deg"] = (
            round(stats["complete"] / stats["total"] * 360) if stats["total"] else 0
        )
    return render(
        request,
        "collection.html",
        {
            "collection": collection,
            "follower_count": follower_count,
            "following": following,
            "stats": stats,
            "available_as_featured": available_as_featured,
            "featured_since": featured_since,
            "editable": collection.is_editable_by(request.user),
        },
    )


@login_required
@require_http_methods(["POST"])
def collection_add_featured(request: AuthedHttpRequest, collection_uuid):
    collection = get_object_or_404(Collection, uid=get_uuid_or_404(collection_uuid))
    if not collection.is_visible_to(request.user):
        raise PermissionDenied(_("Insufficient permission"))
    FeaturedCollection.objects.update_or_create(
        owner=request.user.identity, target=collection
    )
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@require_http_methods(["POST"])
def collection_remove_featured(request: AuthedHttpRequest, collection_uuid):
    collection = get_object_or_404(Collection, uid=get_uuid_or_404(collection_uuid))
    if not collection.is_visible_to(request.user):
        raise PermissionDenied(_("Insufficient permission"))
    fc = FeaturedCollection.objects.filter(
        owner=request.user.identity, target=collection
    ).first()
    if fc:
        fc.delete()
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@require_http_methods(["POST", "GET"])
def collection_share(request: AuthedHttpRequest, collection_uuid):
    collection = get_object_or_404(
        Collection, uid=get_uuid_or_404(collection_uuid) if collection_uuid else None
    )
    if collection and not collection.is_visible_to(request.user):
        raise PermissionDenied(_("Insufficient permission"))
    if request.method == "GET":
        return render(request, "collection_share.html", {"collection": collection})
    else:
        comment = request.POST.get("comment")
        # boost if possible, otherwise quote
        if (
            not comment
            and request.user.preference.mastodon_repost_mode == 0
            and collection.latest_post
        ):
            boost_toot_later(request.user, collection.latest_post.url)
        else:
            visibility = int(request.POST.get("visibility", default=0))
            link = (
                collection.latest_post.url
                if collection.latest_post
                else collection.absolute_url
            )
            if not share_collection(
                collection, comment, request.user, visibility, link
            ):
                return render_relogin(request)
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


def collection_retrieve_items(
    request: AuthedHttpRequest, collection_uuid, edit=False, msg=None
):
    collection = get_object_or_404(Collection, uid=get_uuid_or_404(collection_uuid))
    if not collection.is_visible_to(request.user):
        raise PermissionDenied(_("Insufficient permission"))
    form = CollectionForm(instance=collection)
    return render(
        request,
        "collection_items.html",
        {
            "collection": collection,
            "form": form,
            "collection_edit": edit or request.GET.get("edit"),
            "msg": msg,
        },
    )


@login_required
@require_http_methods(["POST"])
def collection_append_item(request: AuthedHttpRequest, collection_uuid):
    collection = get_object_or_404(Collection, uid=get_uuid_or_404(collection_uuid))
    if not collection.is_editable_by(request.user):
        raise PermissionDenied(_("Insufficient permission"))

    url = request.POST.get("url", "")
    note = request.POST.get("note")
    item = Item.get_by_url(url)
    if item:
        collection.append_item(item, note=note)
        collection.save()
        msg = None
    else:
        msg = _("Unable to find the item, please use item url from this site.")
    return collection_retrieve_items(request, collection_uuid, True, msg)


@login_required
@require_http_methods(["POST"])
def collection_remove_item(request: AuthedHttpRequest, collection_uuid, item_uuid):
    collection = get_object_or_404(Collection, uid=get_uuid_or_404(collection_uuid))
    item = get_object_or_404(Item, uid=get_uuid_or_404(item_uuid))
    if not collection.is_editable_by(request.user):
        raise PermissionDenied(_("Insufficient permission"))
    collection.remove_item(item)
    return collection_retrieve_items(request, collection_uuid, True)


@login_required
@require_http_methods(["POST"])
def collection_move_item(
    request: AuthedHttpRequest, direction, collection_uuid, item_uuid
):
    collection = get_object_or_404(Collection, uid=get_uuid_or_404(collection_uuid))
    if not collection.is_editable_by(request.user):
        raise PermissionDenied(_("Insufficient permission"))
    item = get_object_or_404(Item, uid=get_uuid_or_404(item_uuid))
    if direction == "up":
        collection.move_up_item(item)
    else:
        collection.move_down_item(item)
    return collection_retrieve_items(request, collection_uuid, True)


@login_required
@require_http_methods(["POST"])
def collection_update_member_order(request: AuthedHttpRequest, collection_uuid):
    collection = get_object_or_404(Collection, uid=get_uuid_or_404(collection_uuid))
    if not collection.is_editable_by(request.user):
        raise PermissionDenied(_("Insufficient permission"))
    ids = request.POST.get("member_ids", "").strip()
    if not ids:
        raise BadRequest(_("Invalid parameter"))
    ordered_member_ids = [int(i) for i in ids.split(",")]
    collection.update_member_order(ordered_member_ids)
    return collection_retrieve_items(request, collection_uuid, True)


@login_required
@require_http_methods(["GET", "POST"])
def collection_update_item_note(request: AuthedHttpRequest, collection_uuid, item_uuid):
    collection = get_object_or_404(Collection, uid=get_uuid_or_404(collection_uuid))
    if not collection.is_editable_by(request.user):
        raise PermissionDenied(_("Insufficient permission"))
    item = get_object_or_404(Item, uid=get_uuid_or_404(item_uuid))
    if not collection.is_editable_by(request.user):
        raise PermissionDenied(_("Insufficient permission"))
    if request.method == "POST":
        collection.update_item_metadata(
            item, {"note": request.POST.get("note", default="")}
        )
        return collection_retrieve_items(request, collection_uuid, True)
    else:
        member = collection.get_member_for_item(item)
        return render(
            request,
            "collection_update_item_note.html",
            {"collection": collection, "item": item, "note": member.note},
        )


@login_required
@require_http_methods(["GET", "POST"])
def collection_edit(request: AuthedHttpRequest, collection_uuid=None):
    collection = (
        get_object_or_404(Collection, uid=get_uuid_or_404(collection_uuid))
        if collection_uuid
        else None
    )
    if collection and not collection.is_editable_by(request.user):
        raise PermissionDenied(_("Insufficient permission"))
    if request.method == "GET":
        form = CollectionForm(instance=collection) if collection else CollectionForm()
        if request.GET.get("title"):
            form.instance.title = request.GET.get("title")
        return render(
            request,
            "collection_edit.html",
            {
                "form": form,
                "collection": collection,
                "user": collection.owner.user if collection else request.user,
                "identity": collection.owner if collection else request.user.identity,
            },
        )
    else:
        form = (
            CollectionForm(request.POST, request.FILES, instance=collection)
            if collection
            else CollectionForm(request.POST)
        )
        if form.is_valid():
            if not collection:
                form.instance.owner = request.user.identity
            form.save()
            return redirect(
                reverse("journal:collection_retrieve", args=[form.instance.uuid])
            )
        else:
            raise BadRequest(_("Invalid parameter"))


@target_identity_required
def user_collection_list(request: AuthedHttpRequest, user_name):
    target = request.target_identity
    if not request.user.is_authenticated and not target.anonymous_viewable:
        raise PermissionDenied(_("Login required"))
    collections = (
        Collection.objects.filter(owner=target)
        .filter(q_owned_piece_visible_to_user(request.user, target))
        .order_by("-edited_time")
    )
    return render(
        request,
        "user_collection_list.html",
        {
            "user": target.user,
            "identity": target,
            "collections": collections,
        },
    )


@target_identity_required
def user_liked_collection_list(request: AuthedHttpRequest, user_name):
    target = request.target_identity
    if not request.user.is_authenticated and not target.anonymous_viewable:
        raise PermissionDenied(_("Login required"))
    collections = Collection.objects.filter(
        interactions__identity=target,
        interactions__interaction_type="like",
        interactions__target_type="Collection",
    ).order_by("-edited_time")
    if target.user != request.user:
        collections = collections.filter(q_piece_visible_to_user(request.user))
    return render(
        request,
        "user_collection_list.html",
        {
            "user": target.user,
            "identity": target,
            "collections": collections,
            "liked": True,
        },
    )
