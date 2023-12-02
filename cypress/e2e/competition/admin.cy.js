// TODO: Add view permission tests.
describe("test view permission", () => {
  before(() => {
    cy.resetdb();
    cy.request({ method: 'POST', url: '/competition/test/fill/' });
  });

  it("homepage should return 404 to non-moderators", () => {
    cy.login('alice');
    cy.expectForbidden('/hidden_competition/');
  });

  it("should display the competition homepage to moderators", () => {
    cy.login('moderator0');
    cy.visit('/hidden_competition/');
    cy.get('#sidebar').contains("moderator0"); // Hello, moderator0!
  });
});
