# Generated by Django 4.2.7 on 2023-11-21 00:14

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("journal", "0018_shelflogentrypost_shelflogentry_posts_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="collection",
            name="edited_time",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="collectionmember",
            name="edited_time",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="comment",
            name="edited_time",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="like",
            name="edited_time",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="rating",
            name="edited_time",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="review",
            name="edited_time",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="shelf",
            name="edited_time",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="shelfmember",
            name="edited_time",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="tag",
            name="edited_time",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="tagmember",
            name="edited_time",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
