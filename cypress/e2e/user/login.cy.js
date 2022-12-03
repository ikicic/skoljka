describe("login", () => {
  it("header login form works", () => {
    cy.visit('/');
    cy.get('#hbar-login [name=username]').type("alice");
    cy.get('#hbar-login [name=password]').type("a{enter}");
    cy.contains("Alice");
  });

  it("menu login form works", () => {
    cy.visit('/');
    // There should be a sign in link in the sidebar.
    cy.get('#sidebar [href="/accounts/login/"]').click();
    cy.get('#content [type=text]').type("alice");
    cy.get('#content [type=password]').type("a");
    cy.get('#content [type=submit]').click();
    cy.contains("Alice");  // Hello, Alice!
  });
});
