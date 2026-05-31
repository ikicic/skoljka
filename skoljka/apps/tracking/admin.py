from django.contrib import admin

from skoljka.apps.tracking.models import Bookmark, FavoriteProblemList, FavoriteSource, Like, Submission


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("user", "problem", "solved", "solved_at")
    list_filter = ("solved",)
    search_fields = ("user__username", "problem__title")
    raw_id_fields = ("user", "problem")


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ("user", "problem", "created_at")
    search_fields = ("user__username", "problem__title")
    raw_id_fields = ("user", "problem")


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("user", "problem", "created_at")
    search_fields = ("user__username", "problem__title")
    raw_id_fields = ("user", "problem")


@admin.register(FavoriteSource)
class FavoriteSourceAdmin(admin.ModelAdmin):
    list_display = ("user", "source")
    search_fields = ("user__username", "source__slug")
    raw_id_fields = ("user", "source")


@admin.register(FavoriteProblemList)
class FavoriteProblemListAdmin(admin.ModelAdmin):
    list_display = ("user", "problem_list")
    search_fields = ("user__username", "problem_list__title")
    raw_id_fields = ("user", "problem_list")
