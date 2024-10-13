describe("test chain access", () => {
  beforeEach(() => {
    cy.resetdb();
    cy.request({
      method: 'POST',
      url: '/competition/test/fill/',
      body: {
        'kwargs': { 'min_admin_solved_count': 0 },
      },
    });
  });

  it("test unlock_minutes", () => {
    const COMPETITION = 'public_competition';
    const NOW = 60; // The competitions are set up to have started 60 mins ago.
    const CHAIN_A = { numTasks: 3, position: 100, name: "chain A", unlockMinutes: NOW - 30 };
    const CHAIN_B = { numTasks: 3, position: 150, name: "chain B", unlockMinutes: NOW + 30 };

    cy.login('moderator0');
    cy.createChain(COMPETITION, CHAIN_A).then((chainJsonA) => {
      cy.createChain(COMPETITION, CHAIN_B).then((chainJsonB) => {
        cy.createIndividualTeam(COMPETITION, 'competitor0').then((teamId) => {
          cy.login('competitor0');
          cy.visit(`/${COMPETITION}/task/`);
          cy.contains("chain A").should('exist');
          cy.contains("chain B").should('not.exist');

          // The first ctask of chain A should be accessible.
          cy.visit(`/${COMPETITION}/task/${chainJsonA['ctask_ids'][0]}/`);
          cy.contains("chain A #1");

          // The second ctask of chain A should not be accessible.
          cy.expectNotFound(`/${COMPETITION}/task/${chainJsonA['ctask_ids'][1]}/`);

          // The first ctask of chain B should not be accessible.
          cy.expectNotFound(`/${COMPETITION}/task/${chainJsonB['ctask_ids'][0]}/`);

          // After the competition ends, the chain A should be visible.
          cy.updateCompetition('public_competition', { 'end-hours-after-now': -1 });
          cy.visit(`/${COMPETITION}/task/${chainJsonA['ctask_ids'][2]}/`);

          // However, the chain B should not be visible, because of its
          // unlock_minutes. This allows us to hide a chain indefinitely (by
          // setting unlock_minutes so some very large value).
          cy.expectNotFound(`/${COMPETITION}/task/${chainJsonB['ctask_ids'][0]}/`);
        });
      });
    });
  });
});
