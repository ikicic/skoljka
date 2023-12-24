describe("test scoreboard, categories and sorting", () => {
  const COMPETITION = 'individual_competition_with_categories';
  const RGB = '"hr": {"1": "Crvena", "2": "Zelena", "3": "Plava"}, "en": {"1": "Red", "2": "Green", "3": "Blue"}';
  const HIDDEN = true;
  const VISIBLE = false;

  beforeEach(() => {
    cy.resetdb();
    cy.setlang('en');
    cy.request({ method: 'POST', url: '/competition/test/fill/' });
  });

  function updateCategories(teamCategories) {
    cy.updateCompetition(COMPETITION, { 'team-categories': teamCategories });
  }

  function testTable(selector, hidden_categories, competitors, scores, categories) {
    cy.get(selector).then((trs) => {
      cy.wrap(trs).should('have.length', 1 + competitors.length);

      // Position, [category], name, score.
      cy.wrap(trs[0]).find('th').should('have.length', (hidden_categories ? 3 : 4));

      for (let i = 0; i < competitors.length; ++i) {
        // Manually testing because we are testing many hundreds of conditions.
        const tds = trs[1 + i].children;
        let error = null;
        if (hidden_categories) {
          if (tds[0].innerHTML !== (1 + i).toString()) {
            error = `Bad position for #${i}.`;
          }
          if (tds[1].innerText !== competitors[i]) {
            error = `Bad competitors for #${i}.`;
          }
          if (tds[2].innerHTML !== scores[i].toString()) {
            error = `Bad scores for #${i}.`;
          }
        } else {
          if (tds[0].innerHTML !== (1 + i).toString()) {
            error = `Bad position for #${i}.`;
          }
          if (tds[1].innerHTML !== categories[i]) {
            error = `Bad category for #${i}.`;
          }
          if (tds[2].innerText !== competitors[i]) {
            error = `Bad competitors for #${i}.`;
          }
          if (tds[3].innerHTML !== scores[i].toString()) {
            error = `Bad scores for #${i}.`;
          }
        }
        if (error) {
          throw new Error(
            `Test failed: ${error} Expected: competitors=${competitors}, ` +
            `scores=${scores}, categories=${categories} and correct #`);
        }
      }
    });
  }

  function testWithTeamCategories(hidden) {
    updateCategories(`{${RGB}, "HIDDEN": ${hidden}}`);

    // Test that score is the default sort (for competitions).
    cy.visit(`/${COMPETITION}/scoreboard/`);
    testTable(
      '[data-cy=scoreboard-main] tr',
      hidden,
      ['competitor3', 'competitor0', 'competitor1', 'competitor2'],
      [12, 10, 8, 5],
      ["Blue", "Invalid category", "Red", "Green"]);

    cy.visit(`/${COMPETITION}/scoreboard/?sort=score`);
    testTable(
      '[data-cy=scoreboard-main] tr',
      hidden,
      ['competitor3', 'competitor0', 'competitor1', 'competitor2'],
      [12, 10, 8, 5],
      ["Blue", "Invalid category", "Red", "Green"]);

    cy.visit(`/${COMPETITION}/scoreboard/?sort=name`);
    testTable(
      '[data-cy=scoreboard-main] tr',
      hidden,
      ['competitor0', 'competitor1', 'competitor2', 'competitor3'],
      [10, 8, 5, 12],
      ["Invalid category", "Red", "Green", "Blue"]);
  }

  it("test with visible/hidden team categories", () => {
    cy.createIndividualTeam(COMPETITION, 'competitor0', { category: 0, cacheScore: 10 });
    cy.createIndividualTeam(COMPETITION, 'competitor1', { category: 1, cacheScore: 8 });
    cy.createIndividualTeam(COMPETITION, 'competitor2', { category: 2, cacheScore: 5 });
    cy.createIndividualTeam(COMPETITION, 'competitor3', { category: 3, cacheScore: 12 });

    testWithTeamCategories(VISIBLE);
    testWithTeamCategories(HIDDEN);
  });


  function testInvalidScoreboard(scoreboard) {
    updateCategories(`{${RGB}, "HIDDEN": true, "SCOREBOARD": ${scoreboard}}`);

    cy.visit(`/${COMPETITION}/scoreboard/`);
    testTable('[data-cy=scoreboard-main] tr',
      HIDDEN,
      ['competitor0', 'competitor2', 'competitor1'],
      [10, 8, 5]);
    cy.get('[data-cy=scoreboard-0]').should('not.exist');
  }

  it("test with hidden team categories with invalid SCOREBOARD", () => {
    cy.createIndividualTeam(COMPETITION, 'competitor0', { category: 0, cacheScore: 10 });
    cy.createIndividualTeam(COMPETITION, 'competitor1', { category: 1, cacheScore: 5 });
    cy.createIndividualTeam(COMPETITION, 'competitor2', { category: 2, cacheScore: 8 });

    testInvalidScoreboard('"i-do-not-exist"');
    testInvalidScoreboard('12345');
    testInvalidScoreboard('{}');
    testInvalidScoreboard('{}{{{'); // Test also with a syntax error.
  });

  const NAMES_BY_NAME = [
    'competitor0', 'competitor1', 'competitor2', 'competitor3',
    'competitor4', 'competitor5', 'competitor6'
  ];
  const NAMES_BY_SCORE = [
    'competitor6', 'competitor5', 'competitor0', 'competitor4',
    'competitor3', 'competitor2', 'competitor1'
  ];
  const CATEGORIES_BY_NAME = ["Invalid category", "Red", "Red", "Green", "Green", "Blue", "Blue"];
  const CATEGORIES_BY_SCORE = ["Blue", "Blue", "Invalid category", "Green", "Green", "Red", "Red"];
  const SCORES_BY_NAME = [250, 100, 105, 200, 205, 300, 305];
  const SCORES_BY_SCORE = [305, 300, 250, 205, 200, 105, 100];
  const ALL_BY_NAME = [NAMES_BY_NAME, SCORES_BY_NAME, CATEGORIES_BY_NAME];
  const ALL_BY_SCORE = [NAMES_BY_SCORE, SCORES_BY_SCORE, CATEGORIES_BY_SCORE];
  const RED_BY_NAME = [
    ['competitor1', 'competitor2'],
    [100, 105],
    ["Red", "Red"]
  ];
  const RED_BY_SCORE = [
    ['competitor2', 'competitor1'],
    [105, 100],
    ["Red", "Red"]
  ];
  const GREEN_BY_NAME = [
    ['competitor3', 'competitor4'],
    [200, 205],
    ["Green", "Green"]
  ];
  const GREEN_BY_SCORE = [
    ['competitor4', 'competitor3'],
    [205, 200],
    ["Green", "Green"]
  ];
  const BLUE_BY_NAME = [
    ['competitor5', 'competitor6'],
    [300, 305],
    ["Blue", "Blue"]
  ];
  const BLUE_BY_SCORE = [
    ['competitor6', 'competitor5'],
    [305, 300],
    ["Blue", "Blue"]
  ];

  function testAllAndMyCategory(hidden) {
    updateCategories(`{${RGB}, "HIDDEN": ${hidden}, "SCOREBOARD": "ALL_AND_NONZERO_MY"}`);

    // Not signed in. Test sort by score (default) and by name.
    cy.visit(`/${COMPETITION}/scoreboard/`);
    testTable('[data-cy=scoreboard-main] tr', hidden, ...ALL_BY_SCORE);
    cy.get('[data-cy=scoreboard-0]').should('not.exist');

    cy.get('[data-cy=scoreboard-main] a[data-cy=sort-by-name]').click();
    testTable('[data-cy=scoreboard-main] tr', hidden, ...ALL_BY_NAME);

    cy.get('[data-cy=scoreboard-main] a[data-cy=sort-by-score]').click();
    testTable('[data-cy=scoreboard-main] tr', hidden, ...ALL_BY_SCORE);

    // Signed in and registered. Only one extra table. Test various sort orders.
    cy.login('competitor3');
    cy.setlang('en');
    cy.visit(`/${COMPETITION}/scoreboard/`);
    testTable('[data-cy=scoreboard-main] tr', hidden, ...ALL_BY_SCORE);
    testTable('[data-cy=scoreboard-0] tr', hidden, ...GREEN_BY_SCORE);
    cy.get('[data-cy=scoreboard-1]').should('not.exist');

    cy.get('[data-cy=scoreboard-main] a[data-cy=sort-by-name]').click();
    testTable('[data-cy=scoreboard-main] tr', hidden, ...ALL_BY_NAME);
    testTable('[data-cy=scoreboard-0] tr', hidden, ...GREEN_BY_SCORE);

    cy.get('[data-cy=scoreboard-0] a[data-cy=sort-by-name]').click();
    testTable('[data-cy=scoreboard-main] tr', hidden, ...ALL_BY_NAME);
    testTable('[data-cy=scoreboard-0] tr', hidden, ...GREEN_BY_NAME);

    cy.get('[data-cy=scoreboard-main] a[data-cy=sort-by-score]').click();
    testTable('[data-cy=scoreboard-main] tr', hidden, ...ALL_BY_SCORE);
    testTable('[data-cy=scoreboard-0] tr', hidden, ...GREEN_BY_NAME);

    cy.get('[data-cy=scoreboard-0] a[data-cy=sort-by-score]').click();
    testTable('[data-cy=scoreboard-main] tr', hidden, ...ALL_BY_SCORE);
    testTable('[data-cy=scoreboard-0] tr', hidden, ...GREEN_BY_SCORE);

    // Signed in and registered, but category is #0 (invalid). No extra tables.
    cy.login('competitor0');
    cy.setlang('en');
    cy.visit(`/${COMPETITION}/scoreboard/`);
    testTable('[data-cy=scoreboard-main] tr', hidden, ...ALL_BY_SCORE);
    cy.get('[data-cy=scoreboard-0]').should('not.exist');

    cy.get('[data-cy=scoreboard-main] a[data-cy=sort-by-name]').click();
    testTable('[data-cy=scoreboard-main] tr', hidden, ...ALL_BY_NAME);

    cy.get('[data-cy=scoreboard-main] a[data-cy=sort-by-score]').click();
    testTable('[data-cy=scoreboard-main] tr', hidden, ...ALL_BY_SCORE);
  }

  it("test with visible/hidden team categories and SCOREBOARD == ALL_AND_NONZERO_MY", () => {
    cy.createIndividualTeam(COMPETITION, 'competitor0', { category: 0, cacheScore: 250 });
    cy.createIndividualTeam(COMPETITION, 'competitor1', { category: 1, cacheScore: 100 });
    cy.createIndividualTeam(COMPETITION, 'competitor2', { category: 1, cacheScore: 105 });
    cy.createIndividualTeam(COMPETITION, 'competitor3', { category: 2, cacheScore: 200 });
    cy.createIndividualTeam(COMPETITION, 'competitor4', { category: 2, cacheScore: 205 });
    cy.createIndividualTeam(COMPETITION, 'competitor5', { category: 3, cacheScore: 300 });
    cy.createIndividualTeam(COMPETITION, 'competitor6', { category: 3, cacheScore: 305 });

    testAllAndMyCategory(VISIBLE);
    testAllAndMyCategory(HIDDEN);
  });


  function testWithSeparateScoreboards(hidden, scoreboard) {
    updateCategories(`{${RGB}, "HIDDEN": ${hidden}, "SCOREBOARD": "${scoreboard}"}`);

    // Not signed in.
    cy.logout();
    cy.setlang('en');
    cy.visit(`/${COMPETITION}/scoreboard/`);
    testTable('[data-cy=scoreboard-main] tr', hidden, ...ALL_BY_SCORE);
    testTable('[data-cy=scoreboard-0] tr', hidden, ...RED_BY_SCORE);
    testTable('[data-cy=scoreboard-1] tr', hidden, ...GREEN_BY_SCORE);
    testTable('[data-cy=scoreboard-2] tr', hidden, ...BLUE_BY_SCORE);

    cy.get('[data-cy=scoreboard-main] a[data-cy=sort-by-name]').click();
    testTable('[data-cy=scoreboard-main] tr', hidden, ...ALL_BY_NAME);
    testTable('[data-cy=scoreboard-0] tr', hidden, ...RED_BY_SCORE);
    testTable('[data-cy=scoreboard-1] tr', hidden, ...GREEN_BY_SCORE);
    testTable('[data-cy=scoreboard-2] tr', hidden, ...BLUE_BY_SCORE);

    cy.get('[data-cy=scoreboard-1] a[data-cy=sort-by-name]').click();
    testTable('[data-cy=scoreboard-main] tr', hidden, ...ALL_BY_NAME);
    testTable('[data-cy=scoreboard-0] tr', hidden, ...RED_BY_SCORE);
    testTable('[data-cy=scoreboard-1] tr', hidden, ...GREEN_BY_NAME);
    testTable('[data-cy=scoreboard-2] tr', hidden, ...BLUE_BY_SCORE);

    cy.get('[data-cy=scoreboard-0] a[data-cy=sort-by-name]').click();
    testTable('[data-cy=scoreboard-main] tr', hidden, ...ALL_BY_NAME);
    testTable('[data-cy=scoreboard-0] tr', hidden, ...RED_BY_NAME);
    testTable('[data-cy=scoreboard-1] tr', hidden, ...GREEN_BY_NAME);
    testTable('[data-cy=scoreboard-2] tr', hidden, ...BLUE_BY_SCORE);

    // Signed in (and registered). Test that the current team's category is on top.
    cy.login('competitor3');
    cy.setlang('en');
    cy.visit(`/${COMPETITION}/scoreboard/`);
    testTable('[data-cy=scoreboard-main] tr', hidden, ...ALL_BY_SCORE);
    if (scoreboard == "ALL_AND_NONZERO_EACH") {
      testTable('[data-cy=scoreboard-0] tr', hidden, ...RED_BY_SCORE);
      testTable('[data-cy=scoreboard-1] tr', hidden, ...GREEN_BY_SCORE);
      testTable('[data-cy=scoreboard-2] tr', hidden, ...BLUE_BY_SCORE);

      cy.get('[data-cy=scoreboard-2] a[data-cy=sort-by-name]').click();
      testTable('[data-cy=scoreboard-main] tr', hidden, ...ALL_BY_SCORE);
      testTable('[data-cy=scoreboard-0] tr', hidden, ...RED_BY_SCORE);
      testTable('[data-cy=scoreboard-1] tr', hidden, ...GREEN_BY_SCORE);
      testTable('[data-cy=scoreboard-2] tr', hidden, ...BLUE_BY_NAME);
    } else if (scoreboard == "ALL_AND_NONZERO_MY_THEN_REST") {
      testTable('[data-cy=scoreboard-0] tr', hidden, ...GREEN_BY_SCORE);
      testTable('[data-cy=scoreboard-1] tr', hidden, ...RED_BY_SCORE);
      testTable('[data-cy=scoreboard-2] tr', hidden, ...BLUE_BY_SCORE);

      cy.get('[data-cy=scoreboard-2] a[data-cy=sort-by-name]').click();
      testTable('[data-cy=scoreboard-main] tr', hidden, ...ALL_BY_SCORE);
      testTable('[data-cy=scoreboard-0] tr', hidden, ...GREEN_BY_SCORE);
      testTable('[data-cy=scoreboard-1] tr', hidden, ...RED_BY_SCORE);
      testTable('[data-cy=scoreboard-2] tr', hidden, ...BLUE_BY_NAME);
    } else {
      throw new Error(`Invalid scoreboard: ${scoreboard}`);
    }
  }

  it("test with visible team categories and multiple scoreboards", () => {
    cy.createIndividualTeam(COMPETITION, 'competitor0', { category: 0, cacheScore: 250 });
    cy.createIndividualTeam(COMPETITION, 'competitor1', { category: 1, cacheScore: 100 });
    cy.createIndividualTeam(COMPETITION, 'competitor2', { category: 1, cacheScore: 105 });
    cy.createIndividualTeam(COMPETITION, 'competitor3', { category: 2, cacheScore: 200 });
    cy.createIndividualTeam(COMPETITION, 'competitor4', { category: 2, cacheScore: 205 });
    cy.createIndividualTeam(COMPETITION, 'competitor5', { category: 3, cacheScore: 300 });
    cy.createIndividualTeam(COMPETITION, 'competitor6', { category: 3, cacheScore: 305 });

    testWithSeparateScoreboards(VISIBLE, "ALL_AND_NONZERO_EACH");
    testWithSeparateScoreboards(VISIBLE, "ALL_AND_NONZERO_MY_THEN_REST");
    testWithSeparateScoreboards(HIDDEN, "ALL_AND_NONZERO_EACH");
    testWithSeparateScoreboards(HIDDEN, "ALL_AND_NONZERO_MY_THEN_REST");
  });
});
