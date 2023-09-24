describe("test registration", () => {
  it("test registration using the homepage form", () => {
    cy.resetdb();
    cy.visit('/');
    cy.get('#content [name=username]').type("someusername");
    cy.get('#content [name=email]').type("dummy@skoljka.org");
    cy.get('#content [name=password1]').type("abc");
    cy.get('#content [name=password2]').type("abc");
    cy.get('#content [type=checkbox]').click();
    cy.get('#content [type=submit]').click();

    // Test login does not work before activating the account.
    cy.get('#hbar-login [name=username]').type("someusername");
    cy.get('#hbar-login [name=password]').type("abc{enter}");
    cy.url().should('contain', '/accounts/login/');
    cy.get('[data-cy="login"] .errorlist').contains("This account is inactive.");

    cy.request({
      method: 'GET',
      url: '/test/latest_email/',
    })
      .its('body')
      .then((mail) => {
        cy.wrap(mail).should('contain', 'To: dummy@skoljka.org');

        let site = Cypress._.escapeRegExp(cy.config().baseUrl);
        let pattern = new RegExp(site + '[_/a-zA-Z0-9]*', 'g');
        let links = mail.match(pattern);
        // Two languages.
        cy.wrap(links).should('have.lengthOf', 2);
        cy.wrap(links[0]).should('be.equal', links[1]);

        // Visit the activation link.
        cy.visit(links[0]);
        cy.contains("someusername");            // Hello, someusername!
        cy.get('#content [href="/"]').click();  // Continue button.
        cy.contains("someusername");            // Hello, someusername!
      });
  });

  it("test that non-ascii characters in username and email are rejected", () => {
    cy.resetdb();
    cy.visit('/');
    cy.get('#content [name=username]').type("someusername-š");
    cy.get('#content [name=email]').type("dummy-š@skoljka.org");
    cy.get('#content [name=password1]').type("abc");
    cy.get('#content [name=password2]').type("abc");
    cy.get('#content [type=checkbox]').click();
    cy.get('#content [type=submit]').click();

    cy.url().should('contain', '/accounts/register/');
    cy.get('[data-cy="registration"] [name="username"] + .errorlist').contains("Enter a valid value.");
    cy.get('[data-cy="registration"] [name="email"] + .errorlist').contains("Enter a valid e-mail address.");
  });
});
