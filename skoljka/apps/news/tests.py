from django.test import TestCase

from skoljka.apps.content.models import Content
from skoljka.apps.news.models import NewsPost
from skoljka.tests.factories import make_staff, make_user


class NewsPostViewTest(TestCase):
    def test_news_list_shows_visible_posts(self):
        visible = NewsPost.objects.create(
            title="Visible news",
            slug="visible-news",
            hidden=False,
            created_by=make_user(username="news-author"),
        )
        Content.objects.create(content_object=visible, source_md={"en": "Hello **news**"})
        hidden = NewsPost.objects.create(
            title="Hidden news",
            slug="hidden-news",
            hidden=True,
        )
        undated = NewsPost.objects.create(
            title="Undated visible news",
            slug="undated-visible-news",
            hidden=False,
        )

        r = self.client.get("/news/")

        self.assertContains(r, "Visible news")
        self.assertContains(r, undated.title)
        self.assertContains(r, "<strong>news</strong>")
        self.assertContains(r, "by news-author")
        self.assertNotContains(r, "last edited")
        self.assertNotContains(r, 'href="/news/visible-news/"')
        self.assertNotContains(r, hidden.title)

    def test_news_list_renders_content_with_latex(self):
        post = NewsPost.objects.create(
            title="Latex news",
            slug="latex-news",
            hidden=False,
        )
        Content.objects.create(content_object=post, source_md={"en": "$x^2$"})

        r = self.client.get("/news/")

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'class="katex"')

    def test_hidden_news_is_not_public(self):
        NewsPost.objects.create(
            title="Archived news",
            slug="archived-news",
            hidden=True,
        )

        r = self.client.get("/news/")
        self.assertNotContains(r, "Archived news")

    def test_news_list_edit_link_is_staff_only(self):
        post = NewsPost.objects.create(
            title="Editable news",
            slug="editable-news",
            hidden=False,
        )

        r = self.client.get("/news/")
        self.assertNotContains(r, f"/news/manage/{post.pk}/edit/")

        self.client.force_login(make_staff(username="news-card-admin"))
        r = self.client.get("/news/")
        self.assertContains(r, f'href="/news/manage/{post.pk}/edit/"')
        self.assertContains(r, 'class="news-card-edit"')


class NewsManageViewTest(TestCase):
    def setUp(self):
        self.staff = make_staff(username="news-admin")

    def test_manage_requires_staff(self):
        user = make_user(username="regular-news")
        self.client.force_login(user)
        r = self.client.get("/news/manage/")
        self.assertEqual(r.status_code, 403)

    def test_staff_can_create_news_post_with_content(self):
        self.client.force_login(self.staff)
        r = self.client.post(
            "/news/manage/new/",
            {
                "title": "Created news",
                "slug": "created-news",
                "language": "en",
                "content_md": "Created **body**",
            },
        )

        post = NewsPost.objects.get(slug="created-news")
        self.assertRedirects(r, f"/news/manage/{post.pk}/edit/", fetch_redirect_response=False)
        self.assertFalse(post.hidden)
        self.assertEqual(post.content.get().source_for("en"), "Created **body**")

    def test_staff_can_hide_post(self):
        post = NewsPost.objects.create(
            title="Visible news",
            slug="visible-news-edit",
            hidden=False,
        )
        Content.objects.create(content_object=post, source_md={"en": "Body"})

        self.client.force_login(self.staff)
        r = self.client.post(
            f"/news/manage/{post.pk}/edit/",
            {
                "title": post.title,
                "slug": post.slug,
                "language": "en",
                "content_md": "Body",
                "hidden": "on",
            },
        )

        self.assertRedirects(r, "/news/manage/", fetch_redirect_response=False)
        post.refresh_from_db()
        self.assertTrue(post.hidden)

    def test_staff_can_delete_news_post(self):
        post = NewsPost.objects.create(title="Delete me", slug="delete-me")

        self.client.force_login(self.staff)
        r = self.client.post(f"/news/manage/{post.pk}/delete/")

        self.assertRedirects(r, "/news/manage/", fetch_redirect_response=False)
        self.assertFalse(NewsPost.objects.filter(pk=post.pk).exists())
