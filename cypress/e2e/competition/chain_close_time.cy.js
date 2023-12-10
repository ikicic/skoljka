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

  it("test close_minutes", () => {
    const COMPETITION = 'public_competition';
    const NOW = 60; // The competitions are set up to have started 60 mins ago.
    const CHAIN_A = { numTasks: 3, position: 100, name: "chain A", closeMinutes: NOW - 30 };
    const CHAIN_B = { numTasks: 3, position: 150, name: "chain B", closeMinutes: NOW + 2 };

    cy.login('moderator0');
    cy.setlang('en');
    cy.createChain(COMPETITION, CHAIN_A).then((chainJsonA) => {
      cy.createChain(COMPETITION, CHAIN_B).then((chainJsonB) => {
        cy.createIndividualTeam(COMPETITION, 'competitor0').then((teamId) => {
          cy.login('competitor0');
          cy.setlang('en');
          cy.visit(`/${COMPETITION}/task/`);
          cy.get('tr.comp-chain').should('have.length', 2);
          cy.get('tr.comp-chain').eq(0).contains("chain A");
          cy.get('tr.comp-chain').eq(1).contains("chain B");
          cy.get('tr.comp-chain').eq(0).find('a.ctask').should('have.class', 'ctask-closed');
          cy.get('tr.comp-chain').eq(1).find('a.ctask').should('have.class', 'ctask-open');

          cy.visit(`/${COMPETITION}/task/${chainJsonA['ctask_ids'][0]}/`);
          cy.contains("Submissions are now closed.");
          cy.get('#content form').should('not.exist');

          function check(expectedMessage, minutes) {
            // Add one minute because we the actual time is between NOW and NOW + 1.
            cy.updateChain(chainJsonB['chain_id'], { 'close-minutes': NOW + minutes + 1 });
            cy.reload();
            cy.contains(expectedMessage);
          }

          // First test the "time remaining" in the two languages, to document
          // our expectations (since we rely on the Django's `timeuntil` filter).
          cy.visit(`/${COMPETITION}/task/${chainJsonB['ctask_ids'][0]}/`);
          check("Time remaining: 1 minute", 1);
          check("Time remaining: 2 minutes", 2);
          check("Time remaining: 5 minutes", 5);
          check("Time remaining: 2 hours", 2 * 60 + 5);
          check("Time remaining: 3 days, 2 hours", 3 * 24 * 60 + 2 * 60 + 5);

          cy.setlang('hr');
          // TODO: Check in Django 1.5 if the translations were fixed.
          check("Preostalo vremena: 1 minuta", 1);
          check("Preostalo vremena: 2 minute", 2);
          check("Preostalo vremena: 5 minute", 5); // FIXME: 5 minuta
          check("Preostalo vremena: 1 sat", 1 * 60 + 5);
          check("Preostalo vremena: 2 sati, 5 minute", 2 * 60 + 5); // FIXME: 2 sata
          check("Preostalo vremena: 5 sata, 5 minute", 5 * 60 + 5); // FIXME: 5 sati
          check("Preostalo vremena: 1 dan, 2 sati", 1 * 24 * 60 + 125); // FIXME: 2 sati
          check("Preostalo vremena: 2 dani, 2 sati", 2 * 24 * 60 + 125); // FIXME: 2 dana, 2 sata
          check("Preostalo vremena: 5 dana, 2 sati", 5 * 24 * 60 + 125); // FIXME: 2 sata

          // Test that submitting a solution works.
          cy.setlang('en');
          cy.get('#id_result').type("100{enter}");
          cy.get('.ctask-submissions-table span.label.label-success').contains("Correct");
          cy.get('a.btn').contains("Next problem");
        });
      });
    });
  });
});
