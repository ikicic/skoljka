describe("login", () => {
  it("test login using the header form", () => {
    cy.visit('/');
    cy.get('#hbar-login [name=username]').type("alice");
    cy.get('#hbar-login [name=password]').type("a{enter}");
    cy.contains("Alice"); // Signed in. ("Hello, Alice!")
  });

  it("test login using the menu form", () => {
    cy.visit('/');
    // There should be a sign in link in the sidebar.
    cy.get('#sidebar [href="/accounts/login/"]').click();
    cy.get('#content [type=text]').type("alice");
    cy.get('#content [type=password]').type("a");
    cy.get('#content [type=submit]').click();
    cy.contains("Alice"); // Signed in. ("Hello, Alice!")
  });

  it("test failed header login", () => {
    cy.visit('/');
    cy.get('#hbar-login [name=username]').type("idonotexist");
    cy.get('#hbar-login [name=password]').type("a{enter}");
    cy.url().should('contain', '/accounts/login/');
    cy.get('[data-cy="login"] .alert-error').contains("Please enter a correct username and password.");
  });

  it("test failed menu login", () => {
    cy.visit('/');
    cy.get('#sidebar [href="/accounts/login/"]').click();
    cy.get('#content [type=text]').type("idonotexist");
    cy.get('#content [type=password]').type("a{enter}");
    cy.url().should('contain', '/accounts/login/');
    cy.get('[data-cy="login"] .alert-error').contains("Please enter a correct username and password.");
  });
});
