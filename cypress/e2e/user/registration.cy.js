describe("test registration", () => {
  function testRegistration() {
    cy.get('#content [name=username]').type("someusername");
    cy.get('#content [name=email]').type("dummy@skoljka.org");
    cy.get('#content [name=password1]').type("abc");
    cy.get('#content [name=password2]').type("abc");
    cy.get('#content [name=ca]').type("70"); // Challenge answer. 50 + sqrt(400)
    cy.get('#content [type=checkbox]').click();
    cy.get('#content [type=submit]').click();

    // Test login does not work before activating the account.
    cy.get('#hbar-login [name=username]').type("someusername");
    cy.get('#hbar-login [name=password]').type("abc{enter}");
    cy.location('pathname').should('eq', '/accounts/login/');
    cy.get('[data-cy="login"] .alert-error').contains("This account is inactive.");

    // Test login works after confirming the email.
    cy.request({ method: 'GET', url: '/test/latest_email/' })
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
        cy.contains("someusername"); // Hello, someusername!
        cy.get('#content [href="/"]').click(); // Continue button.
        cy.contains("someusername"); // Hello, someusername!
      });
  }

  it("test registration using the homepage form", () => {
    cy.resetdb();
    cy.visit('/?test_registration_challenge=5');
    testRegistration();
  });

  it("test the dedicated registration page", () => {
    cy.resetdb();
    cy.visit('/accounts/register/?test_registration_challenge=5');
    testRegistration();
  });

  it("test that non-ascii characters in username and email are rejected", () => {
    cy.resetdb();
    cy.visit('/');
    cy.get('#content [name=username]').type("someusername-š");
    cy.get('#content [name=email]').type("dummy-š@skoljka.org");
    cy.get('#content [name=password1]').type("abc");
    cy.get('#content [name=password2]').type("abc");
    cy.get('#content [name=ca]').type("12345");
    cy.get('#content [type=submit]').click();

    cy.location('pathname').should('eq', '/accounts/register/');
    cy.get('[data-cy="registration"] [name="username"] + .help-block').contains("Enter a valid value.");
    cy.get('[data-cy="registration"] [name="email"] + .help-block').contains("Enter a valid e-mail address.");
    cy.get('[data-cy="registration"] [class="checkbox"] + .help-block').contains(
      "You may not use Školjka if you do not accept the Terms of Use.");
  });

  it("test incorrect challenge answer", () => {
    cy.resetdb();
    cy.setlang('en');
    cy.visit('/?test_registration_challenge=5');
    cy.get('#content [name=username]').type("someusername");
    cy.get('#content [name=email]').type("dummy@skoljka.org");
    cy.get('#content [name=password1]').type("abc");
    cy.get('#content [name=password2]').type("abc");
    cy.get('#content [name=ca]').type("12345"); // Should be 70 (50 + sqrt(400)).
    cy.get('#content [type=checkbox]').click();
    cy.get('#content [type=submit]').click();
    cy.get('#content [name=ca]').should('have.value', ""); // Should be empty.
    cy.get('.reg-ch-outer').should('have.class', 'error');
    cy.get('.reg-ch-outer').contains("Incorrect answer, please try again.");
  });
});
