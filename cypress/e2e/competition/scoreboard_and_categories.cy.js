describe("test scoreboard and categories", () => {
  const COMPETITION = 'individual_competition_with_categories';
  const RGB = '"hr": {"1": "Crvena", "2": "Zelena", "3": "Plava"}, "en": {"1": "Red", "2": "Green", "3": "Blue"}';
  const HIDDEN = true;
  const VISIBLE = false;

  beforeEach(() => {
    cy.resetdb();
    cy.setlang('en');
  });

  function fillWithCategories(team_categories) {
    cy.request({
      method: 'POST',
      url: '/competition/test/fill/',
      body: {
        'kwargs': { 'team_categories': team_categories },
      },
    });
  }

  function testTable(selector, hidden_categories, competitors, categories) {
    cy.get(selector).then((trs) => {
      cy.wrap(trs).should('have.length', 1 + competitors.length);

      // Position, [category], name, score.
      cy.wrap(trs[0]).find('th').should('have.length', (hidden_categories ? 3 : 4));

      for (let i = 0; i < competitors.length; ++i) {
        cy.wrap(trs[1 + i]).find('td').then((tds) => {
          if (hidden_categories) {
            expect(tds[0]).to.have.text("1"); // Position.
            expect(tds[1]).to.have.text(competitors[i]);
            expect(tds[2]).to.have.text("0"); // Score.
          } else {
            expect(tds[0]).to.have.text("1"); // Position.
            expect(tds[1]).to.have.text(categories[i]);
            expect(tds[2]).to.have.text(competitors[i]);
            expect(tds[3]).to.have.text("0"); // Score.
          }
        });
      }
    });
  }

  function testWithTeamCategories(hidden) {
    fillWithCategories(`{${RGB}, "HIDDEN": ${hidden}}`);

    cy.createIndividualTeam(COMPETITION, 'competitor1', { category: 1 });
    cy.createIndividualTeam(COMPETITION, 'competitor2', { category: 2 });
    cy.createIndividualTeam(COMPETITION, 'competitor3', { category: 3 });

    cy.visit(`/${COMPETITION}/scoreboard/`);
    testTable(
      '[data-cy=scoreboard-main] tr',
      hidden,
      ['competitor1', 'competitor2', 'competitor3'],
      ["Red", "Green", "Blue"]);
  }

  it("test with visible team categories", () => {
    testWithTeamCategories(VISIBLE);
  });

  it("test with hidden team categories", () => {
    testWithTeamCategories(HIDDEN);
  });


  function testInvalidScoreboard(scoreboard) {
    fillWithCategories(`{${RGB}, "HIDDEN": true, "SCOREBOARD": ${scoreboard}}`);

    cy.createIndividualTeam(COMPETITION, 'competitor1', { category: 1 });
    cy.createIndividualTeam(COMPETITION, 'competitor2', { category: 2 });

    cy.visit(`/${COMPETITION}/scoreboard/`);
    testTable('[data-cy=scoreboard-main] tr', HIDDEN, ['competitor1', 'competitor2']);
    cy.get('[data-cy=scoreboard-0]').should('not.exist');
  }

  it("test with hidden team categories with invalid SCOREBOARD (str)", () => {
    testInvalidScoreboard('"i-do-not-exist"');
  });

  it("test with hidden team categories with invalid SCOREBOARD (int)", () => {
    testInvalidScoreboard('12345');
  });

  it("test with hidden team categories with invalid SCOREBOARD (dict)", () => {
    testInvalidScoreboard('{}');
  });


  function testAllAndMyCategory(hidden) {
    fillWithCategories(`{${RGB}, "HIDDEN": ${hidden}, "SCOREBOARD": "ALL_AND_MY_CATEGORY"}`);
    const ALL = ['competitor1', 'competitor2', 'competitor3', 'competitor4', 'competitor5', 'competitor6'];
    const ALL_CATEGORIES = ["Red", "Red", "Green", "Green", "Blue", "Blue"];

    cy.createIndividualTeam(COMPETITION, 'competitor1', { category: 1 });
    cy.createIndividualTeam(COMPETITION, 'competitor2', { category: 1 });
    cy.createIndividualTeam(COMPETITION, 'competitor3', { category: 2 });
    cy.createIndividualTeam(COMPETITION, 'competitor4', { category: 2 });
    cy.createIndividualTeam(COMPETITION, 'competitor5', { category: 3 });
    cy.createIndividualTeam(COMPETITION, 'competitor6', { category: 3 });

    // Not signed in.
    cy.visit(`/${COMPETITION}/scoreboard/`);
    testTable('[data-cy=scoreboard-main] tr', hidden, ALL, ALL_CATEGORIES);
    cy.get('[data-cy=scoreboard-0]').should('not.exist');

    // Signed in (and registered). Only one extra table.
    cy.login('competitor3');
    cy.setlang('en');
    cy.visit(`/${COMPETITION}/scoreboard/`);
    testTable('[data-cy=scoreboard-main] tr', hidden, ALL, ALL_CATEGORIES);
    testTable('[data-cy=scoreboard-0] tr', hidden, ['competitor3', 'competitor4'], ["Green", "Green"]);
    cy.get('[data-cy=scoreboard-1]').should('not.exist');
  }

  it("test with visible team categories and SCOREBOARD == ALL_AND_MY_CATEGORY", () => {
    testAllAndMyCategory(VISIBLE);
  });

  it("test with hidden team categories and SCOREBOARD == ALL_AND_MY_CATEGORY", () => {
    testAllAndMyCategory(HIDDEN);
  });


  function testWithSeparateScoreboards(hidden, scoreboard) {
    fillWithCategories(`{${RGB}, "HIDDEN": ${hidden}, "SCOREBOARD": "${scoreboard}"}`);
    const ALL = ['competitor1', 'competitor2', 'competitor3', 'competitor4', 'competitor5', 'competitor6'];
    const ALL_CATEGORIES = ["Red", "Red", "Green", "Green", "Blue", "Blue"];

    cy.createIndividualTeam(COMPETITION, 'competitor1', { category: 1 });
    cy.createIndividualTeam(COMPETITION, 'competitor2', { category: 1 });
    cy.createIndividualTeam(COMPETITION, 'competitor3', { category: 2 });
    cy.createIndividualTeam(COMPETITION, 'competitor4', { category: 2 });
    cy.createIndividualTeam(COMPETITION, 'competitor5', { category: 3 });
    cy.createIndividualTeam(COMPETITION, 'competitor6', { category: 3 });

    // Not signed in.
    cy.visit(`/${COMPETITION}/scoreboard/`);
    testTable('[data-cy=scoreboard-main] tr', hidden, ALL, ALL_CATEGORIES);
    testTable('[data-cy=scoreboard-0] tr', hidden, ['competitor1', 'competitor2'], ["Red", "Red"]);
    testTable('[data-cy=scoreboard-1] tr', hidden, ['competitor3', 'competitor4'], ["Green", "Green"]);
    testTable('[data-cy=scoreboard-2] tr', hidden, ['competitor5', 'competitor6'], ["Blue", "Blue"]);

    // Signed in (and registered). Test that the current team's category is on top.
    cy.login('competitor3');
    cy.setlang('en');
    cy.visit(`/${COMPETITION}/scoreboard/`);
    testTable('[data-cy=scoreboard-main] tr', hidden, ALL, ALL_CATEGORIES);
    if (scoreboard == "ALL_AND_PER_CATEGORY") {
      testTable('[data-cy=scoreboard-0] tr', hidden, ['competitor1', 'competitor2'], ["Red", "Red"]);
      testTable('[data-cy=scoreboard-1] tr', hidden, ['competitor3', 'competitor4'], ["Green", "Green"]);
      testTable('[data-cy=scoreboard-2] tr', hidden, ['competitor5', 'competitor6'], ["Blue", "Blue"]);
    } else if (scoreboard == "ALL_AND_MY_THEN_REST") {
      testTable('[data-cy=scoreboard-0] tr', hidden, ['competitor3', 'competitor4'], ["Green", "Green"]);
      testTable('[data-cy=scoreboard-1] tr', hidden, ['competitor1', 'competitor2'], ["Red", "Red"]);
      testTable('[data-cy=scoreboard-2] tr', hidden, ['competitor5', 'competitor6'], ["Blue", "Blue"]);
    } else {
      throw new Error(`Invalid scoreboard: ${scoreboard}`);
    }
  }

  it("test with visible team categories and SCOREBOARD == ALL_AND_PER_CATEGORY", () => {
    testWithSeparateScoreboards(VISIBLE, "ALL_AND_PER_CATEGORY");
  });

  it("test with visible team categories and SCOREBOARD == ALL_AND_MY_THEN_REST", () => {
    testWithSeparateScoreboards(VISIBLE, "ALL_AND_MY_THEN_REST");
  });

  it("test with hidden team categories and SCOREBOARD == ALL_AND_PER_CATEGORY", () => {
    testWithSeparateScoreboards(HIDDEN, "ALL_AND_PER_CATEGORY");
  });

  it("test with hidden team categories and SCOREBOARD == ALL_AND_MY_THEN_REST", () => {
    testWithSeparateScoreboards(HIDDEN, "ALL_AND_MY_THEN_REST");
  });
});
