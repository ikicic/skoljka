describe("test scoreboard and categories", () => {
  const COMPETITION = 'individual_competition_with_categories';

  function checkWithoutCategories() {
    cy.setlang('en');
    cy.visit(`/${COMPETITION}/scoreboard/`);
    cy.get('[data-cy=scoreboard] tr').then((trs) => {
      cy.wrap(trs).should('have.length', 4); // 4 rows.
      cy.wrap(trs[0]).find('th').should('have.length', 3); // #, name, score.
      cy.wrap(trs[1]).find('td').eq(0).contains("1");
      cy.wrap(trs[2]).find('td').eq(0).contains("1");
      cy.wrap(trs[3]).find('td').eq(0).contains("1");
      cy.wrap(trs[1]).find('td').eq(1).contains("competitor1");
      cy.wrap(trs[2]).find('td').eq(1).contains("competitor2");
      cy.wrap(trs[3]).find('td').eq(1).contains("competitor3");
      cy.wrap(trs[1]).find('td').eq(2).contains("0");
      cy.wrap(trs[2]).find('td').eq(2).contains("0");
      cy.wrap(trs[3]).find('td').eq(2).contains("0");
    });
  }

  function checkWithCategories() {
    cy.setlang('en');
    cy.visit(`/${COMPETITION}/scoreboard/`);
    cy.get('[data-cy=scoreboard] tr').then((trs) => {
      cy.wrap(trs).should('have.length', 4); // 4 rows.
      cy.wrap(trs[0]).find('th').should('have.length', 4); // #, category, name, score.
      cy.wrap(trs[1]).find('td').eq(0).contains("1");
      cy.wrap(trs[2]).find('td').eq(0).contains("1");
      cy.wrap(trs[3]).find('td').eq(0).contains("1");
      cy.wrap(trs[1]).find('td').eq(1).contains("Red");
      cy.wrap(trs[2]).find('td').eq(1).contains("Green");
      cy.wrap(trs[3]).find('td').eq(1).contains("Blue");
      cy.wrap(trs[1]).find('td').eq(2).contains("competitor1");
      cy.wrap(trs[2]).find('td').eq(2).contains("competitor2");
      cy.wrap(trs[3]).find('td').eq(2).contains("competitor3");
      cy.wrap(trs[1]).find('td').eq(3).contains("0");
      cy.wrap(trs[2]).find('td').eq(3).contains("0");
      cy.wrap(trs[3]).find('td').eq(3).contains("0");
    });
  }

  beforeEach(() => {
    cy.resetdb();
  });

  it("test scoreboard with visible team categories", () => {
    cy.request({ method: 'POST', url: '/competition/test/fill/' });

    cy.createIndividualTeam(COMPETITION, 'competitor1', { category: 1 });
    cy.createIndividualTeam(COMPETITION, 'competitor2', { category: 2 });
    cy.createIndividualTeam(COMPETITION, 'competitor3', { category: 3 });

    checkWithCategories();
  });

  it("test scoreboard with hidden team categories", () => {
    const TEAM_CATEGORIES =
      '{"hr": {"1": "Crvena", "2": "Zelena", "3": "Plava"}, "en": {"1": "Red", "2": "Green", "3": "Blue"}, "HIDDEN": true}';

    cy.request({
      method: 'POST',
      url: '/competition/test/fill/',
      body: {
        'kwargs': { 'team_categories': TEAM_CATEGORIES },
      },
    });

    cy.createIndividualTeam(COMPETITION, 'competitor1', { category: 1 });
    cy.createIndividualTeam(COMPETITION, 'competitor2', { category: 2 });
    cy.createIndividualTeam(COMPETITION, 'competitor3', { category: 3 });

    // For non-admins.
    checkWithoutCategories();

    // For admins.
    cy.login('moderator0');
    checkWithCategories();
  });
});
