from django import template

from journal.models.mark import Mark
from takahe.utils import Takahe

register = template.Library()


@register.simple_tag(takes_context=True)
def get_mark_for_item(context, item):
    user = context["request"].user
    return (
        Mark(user.identity, item) if user and user.is_authenticated and item else None
    )


@register.simple_tag(takes_context=True)
def liked_piece(context, piece):
    user = context["request"].user
    return user and user.is_authenticated and piece.is_liked_by(user.identity)


@register.simple_tag(takes_context=True)
def liked_post(context, post):
    if post.liked_by_current_user is not None:
        return post.liked_by_current_user
    user = context["request"].user
    return (
        user
        and user.is_authenticated
        and post.interactions.filter(
            identity_id=user.identity.pk, type="like", state__in=["new", "fanned_out"]
        ).exists()
    )


@register.simple_tag(takes_context=True)
def boosted_post(context, post):
    if post.boosted_by_current_user is not None:
        return post.boosted_by_current_user
    user = context["request"].user
    return (
        user
        and user.is_authenticated
        and post.interactions.filter(
            identity_id=user.identity.pk, type="boost", state__in=["new", "fanned_out"]
        ).exists()
    )


@register.simple_tag(takes_context=True)
def pinned_post(context, post):
    user = context["request"].user
    return (
        user
        and user.is_authenticated
        and post.interactions.filter(
            identity_id=user.identity.pk, type="pin", state__in=["new", "fanned_out"]
        ).exists()
    )


@register.simple_tag(takes_context=True)
def post_vote_info(context, post):
    user = context["request"].user
    if not user or not user.is_authenticated or not post or post.type != "Question":
        return {}
    return Takahe.get_poll_info(post, user.identity.pk)
