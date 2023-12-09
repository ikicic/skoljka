describe("test admin team list", () => {
  const COMPETITION = 'individual_competition_with_categories';

  beforeEach(() => {
    cy.resetdb();
  });

  it("test competitions with team categories", () => {
    cy.request({ method: 'POST', url: '/competition/test/fill/' });

    cy.createIndividualTeam(COMPETITION, 'competitor1', { category: 1 });
    cy.createIndividualTeam(COMPETITION, 'competitor2', { category: 2 });
    cy.createIndividualTeam(COMPETITION, 'competitor3', { category: 3 });
    cy.createIndividualTeam(COMPETITION, 'competitor4', { category: 10 }); // Does not exist.

    cy.login('moderator0');
    cy.setlang('en');
    cy.visit(`/${COMPETITION}/team/list/admin/`);

    cy.get('[name=team-1-category] option:selected').should('have.text', "Red");
    cy.get('[name=team-2-category] option:selected').should('have.text', "Green");
    cy.get('[name=team-3-category] option:selected').should('have.text', "Blue");
    cy.get('[name=team-4-category] option:selected').should('have.text', "Invalid category #10");
    cy.get('[name=team-1-category]').select("Green"); // Keep team 2 category as is.
    cy.get('[name=team-3-category]').select("Red");
    cy.get('[name=team-4-category]').select("Green");
    cy.get('[data-cy=continue-with-team-changes]').click();

    cy.get('ul[data-cy=changes-confirmation] li').should('have.length', 3);
    cy.contains("Change the category of the team \"competitor1\" from \"Red\" to \"Green\".");
    cy.contains("Change the category of the team \"competitor2\"").should('not.exist');
    cy.contains("Change the category of the team \"competitor3\" from \"Blue\" to \"Red\".");
    cy.contains("Change the category of the team \"competitor4\" from \"Invalid category #10\" to \"Green\".");
    cy.get('[data-cy=confirm-changes-form] [type=hidden]').should('have.length', 3 + 1); // 1 for csrf_token;
    cy.get('[data-cy=confirm-changes]').click()

    cy.get('[name=team-1-category] option:selected').should('have.text', "Green");
    cy.get('[name=team-2-category] option:selected').should('have.text', "Green");
    cy.get('[name=team-3-category] option:selected').should('have.text', "Red");
    cy.get('[name=team-4-category] option:selected').should('have.text', "Green");
  });
});
