describe("test chain access", () => {
  const COMPETITION = 'public_competition';
  const NOW = 60; // The competitions are set up to have started 60 mins ago.
  const chainJsons = {};

  before(() => {
    cy.resetdb();
    cy.request({
      method: 'POST',
      url: '/competition/test/fill/',
      body: {
        'kwargs': { 'min_admin_solved_count': 0 },
      },
    });

    const COMMON = { numTasks: 3, maxScore: 2 };
    const CHAINS = [
      { name: "A: closed, automatic", closeMinutes: NOW - 30 },
      { name: "B: open, automatic", closeMinutes: NOW + 30 },
      { name: "C: closed, manual", closeMinutes: NOW - 30, descriptor: 'MANUAL' },
      { name: "D: open, manual", closeMinutes: NOW + 30, descriptor: 'MANUAL' },
    ];

    cy.login('moderator0');
    for (let i = 0; i < CHAINS.length; ++i) {
      const options = { ...COMMON, ...CHAINS[i], position: 100 * i };
      cy.createChain(COMPETITION, options).then((chainJson) => {
        chainJsons[CHAINS[i]['name'][0]] = chainJson;
      });
    }

    cy.createIndividualTeam(COMPETITION, 'competitor0');
    cy.login('competitor0');
    cy.setlang('en');
  });

  beforeEach(() => {
    cy.login('competitor0');
    cy.setlang('en');
  });

  function visitChainCtask(chain, ctaskIndex) {
    const chainJson = chainJsons[chain];
    const ctaskId = chainJson['ctask_ids'][ctaskIndex];
    cy.visit(`/${COMPETITION}/task/${ctaskId}/`);
  }

  it("test chain list", () => {
    cy.login('competitor0');
    cy.setlang('en');
    cy.visit(`/${COMPETITION}/task/`);
    cy.get('tr.comp-chain').then((trs) => {
      expect(trs).to.have.length(4);
      expect(trs[0]).to.contain("A: closed, automatic");
      expect(trs[1]).to.contain("B: open, automatic");
      expect(trs[2]).to.contain("C: closed, manual");
      expect(trs[3]).to.contain("D: open, manual");
      cy.wrap(trs[0]).find('a.ctask').should('have.class', 'ctask-closed');
      cy.wrap(trs[1]).find('a.ctask').should('have.class', 'ctask-open');
      cy.wrap(trs[2]).find('a.ctask').should('have.class', 'ctask-closed');
      cy.wrap(trs[3]).find('a.ctask').should('have.class', 'ctask-open');
    });
  });

  it("test remaining time", () => {
    function check(expectedMessage, minutes) {
      // Add one minute because we the actual time is between NOW and NOW + 1.
      cy.updateChain(chainJsons['B']['chain_id'], { 'close-minutes': NOW + minutes + 1 });
      cy.reload();
      cy.contains(expectedMessage);
    }

    // First test the "time remaining" in the two languages, to document
    // our expectations (since we rely on the Django's `timeuntil` filter).
    visitChainCtask('B', 0);
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

    // Reset to the old value.
    check("Preostalo vremena: 29 minute", 29); // FIXME: 29 minuta
  });

  it("test chain A: closed, automatic", () => {
    visitChainCtask('A', 0);
    cy.contains("Submissions are now closed.");
    cy.get('#content form').should('not.exist');
  });

  it("test chain B: open, automatic", () => {
    visitChainCtask('B', 0);
    cy.contains("Time remaining: 29 minutes")
    cy.contains("Submissions are now closed.").should('not.exist');
    cy.get('#content form').should('exist');

    // Test submitting a solution.
    cy.setlang('en');
    cy.get('#id_result').type("100{enter}");
    cy.get('.ctask-submissions-table span.label.label-success').contains("Correct");
    cy.get('a.btn').contains("Next problem");
    cy.contains("Time remaining: 29 minutes").should('not.exist');
    cy.contains("Submissions are now closed.").should('not.exist');

    // Test the GUI after the time expires.
    cy.updateChain(chainJsons['B']['chain_id'], { 'close-minutes': NOW - 30 });
    cy.reload();
    cy.get('.ctask-submissions-table span.label.label-success').contains("Correct");
    cy.get('a.btn').contains("Next problem");
    cy.contains("Time remaining: 29 minutes").should('not.exist');
    cy.contains("Submissions are now closed.").should('not.exist');
  });

  it("test chain C: closed, automatic", () => {
    visitChainCtask('C', 0);
    cy.contains("Submissions are now closed.");
    cy.get('#content form').should('not.exist');
  });

  it("test chain D: closed, automatic", () => {
    visitChainCtask('D', 0);
    cy.contains("Time remaining: 29 minutes")
    cy.contains("Submissions are now closed.").should('not.exist');
    cy.get('#content form').should('exist');

    // Test submitting a solution.
    cy.get('#id_text').type("some solution");
    cy.get('[data-cy=submit-solution]').click();

    cy.get('[data-cy=ctask-answer]').contains("some solution");
    cy.get('[data-cy=save-solution]').should('exist');
    cy.get('[data-cy=submit-solution]').should('not.exist');
    cy.contains("Time remaining: 29 minutes")

    // Test the GUI after the time expires.
    cy.updateChain(chainJsons['D']['chain_id'], { 'close-minutes': NOW - 30 });
    cy.reload();

    cy.get('[data-cy=ctask-answer]').contains("some solution");
    cy.get('[data-cy=save-solution]').should('not.exist');
    cy.get('[data-cy=submit-solution]').should('not.exist');
    cy.contains("Submissions are now closed.");

    // Test that commenting still works.
    cy.get('#post textarea').type("some comment");
    cy.get('#post [type=submit]').click();
    cy.get('.post').contains("some comment").should('exist');
  });
});
