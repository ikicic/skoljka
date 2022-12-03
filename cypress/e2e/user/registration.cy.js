describe("test registration", () => {
  it("homepage registration form works", () => {
    cy.resetdb();
    cy.visit('/');
    cy.get('#content [name=username]').type("someusername");
    cy.get('#content [name=email]').type("dummy@skoljka.org");
    cy.get('#content [name=password1]').type("abc");
    cy.get('#content [name=password2]').type("abc");
    cy.get('#content [type=checkbox]').click();
    cy.get('#content [type=submit]').click();
    cy.request({
      method: 'GET',
      url: '/test/latest_email/',
    })
      .its('body')
      .then((mail) => {
        console.log(typeof(mail));
        console.log(mail);
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
});
