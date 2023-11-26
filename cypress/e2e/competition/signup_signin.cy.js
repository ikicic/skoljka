describe("test sign in and account registration", () => {
  beforeEach(() => {
    cy.resetdb();
    cy.request({ method: 'POST', url: '/competition/test/fill/' });
    cy.setlang('en');
    cy.visit('/public_competition/registration/');
  });

  it("test that sign-in leads to the team registration page", () => {
    cy.get('#id_username').type("competitor0");
    cy.get('#id_password').type("a");
    cy.get('[data-cy="login"] [type="submit"]').click();

    cy.location('pathname').should('eq', '/public_competition/registration/');
    cy.get('#sidebar').contains("Hello, competitor0!");
  });

  it("test that a failed sign-in still remembers the target URL", () => {
    cy.get('#id_username').type("competitor0");
    cy.get('#id_password').type("wrong_password");
    cy.get('[data-cy="login"] [type="submit"]').click();

    cy.location('pathname').should('eq', '/accounts/login/');
    cy.get('#id_username').should('have.value', "competitor0");
    cy.get('#id_password').type("a");
    cy.get('[data-cy="login"] [type="submit"]').click();

    cy.location('pathname').should('eq', '/public_competition/registration/');
    cy.get('#sidebar').contains("Hello, competitor0!");
  });

  it("test account registration", () => {
    cy.visit('/public_competition/registration/?test_registration_challenge=5');
    cy.get('[data-cy=registration] [name=username]').type("someusername");
    cy.get('[data-cy=registration] [name=email]').type("dummy@skoljka.org");
    cy.get('[data-cy=registration] [name=password1]').type("abc");
    cy.get('[data-cy=registration] [name=password2]').type("abc");
    cy.get('[data-cy=registration] [name=ca]').type("70"); // 50 + sqrt(400)
    cy.get('[data-cy=registration] [type=checkbox]').click();
    cy.get('[data-cy=registration] [type=submit]').click();

    cy.location('pathname').should('eq', '/accounts/register/complete/');
    cy.location('search').should('match', /^\?email=.*$/);
    cy.contains("Thank you for signing up!");
  });
});
