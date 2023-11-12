describe("test courses", () => {
  beforeEach(() => {
    cy.resetdb();
    cy.request({ method: 'POST', url: '/competition/test/fill/' });
  });

  it("test that the restricted_access field is after unlock_days", () => {
    // unlock_days is inserted manually, which automatically puts it at the end
    // of the form. However, we want to keep the restricted_access at the end.
    cy.login('moderator0');
    cy.visit('/individual_course_without_categories/chain/tasks/');
    cy.get('[data-cy=create-chain] .control-group').eq(-3).find('#id_unlock_mode').should('exist');
    cy.get('[data-cy=create-chain] .control-group').eq(-2).find('#id_unlock_days').should('exist');
    cy.get('[data-cy=create-chain] .control-group').eq(-1).find('#id_restricted_access').should('exist');
  });
});
