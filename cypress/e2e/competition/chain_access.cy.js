describe("test chain access", () => {
  beforeEach(() => {
    cy.resetdb();
    cy.request({ method: 'POST', url: '/competition/test/fill/' });
  });

  it("test editing chain-team access with categories", () => {
    const COMPETITION = 'individual_competition_with_categories';
    const CHAIN = { numTasks: 3, position: 50, name: "some chain name" };

    cy.login('moderator0');
    cy.setlang('en');
    cy.visit(`/${COMPETITION}/chain/tasks/`);
    cy.createChain(COMPETITION, CHAIN).then((chainJson) => {
      // Start with an unrestricted chain. There should be no form for editing access rights.
      const chainId = chainJson['chain_id'];
      cy.visit(`/${COMPETITION}/chain/${chainId}/`);
      cy.get('input[name=restricted_access]').should('not.be.checked');
      cy.contains("Chain visibility").should('not.exist');
      cy.get('input[name=restricted_access]').check();
      cy.get('input[name=restricted_access]').should('be.checked');
      cy.get('[data-cy=submit-chain]').click();

      cy.get('input[name=restricted_access]').should('be.checked');
      cy.contains("Chain visibility").should('exist');
      cy.contains("No participants yet.").should('exist');

      // Create two teams.
      cy.createIndividualTeam(COMPETITION, 'competitor0', { category: 1 }).then((teamId0) => {
        cy.createIndividualTeam(COMPETITION, 'competitor1', { category: 2 }).then((teamId1) => {
          cy.reload();
          cy.contains("No participants yet.").should('not.exist');
          cy.get('#chain-access-table th').should('have.length', 3); // Category, team, checkbox.
          cy.get('#chain-access-table input[type=checkbox]').should('have.length', 2);
          cy.get(`[name=team-${teamId0}]`).should('not.be.checked');
          cy.get(`[name=team-${teamId1}]`).should('not.be.checked');

          // Check the second.
          cy.get(`[name=team-${teamId1}]`).myCheck();
          cy.get(`[name=team-${teamId1}]`).should('be.checked');
          cy.get('[data-cy=change-chain-access]').click();
          cy.get(`[name=team-${teamId0}]`).should('not.be.checked');
          cy.get(`[name=team-${teamId1}]`).should('be.checked');

          // Check the first. Uncheck second.
          cy.get(`[name=team-${teamId0}]`).myCheck();
          cy.get(`[name=team-${teamId1}]`).myUncheck();
          cy.get('[data-cy=change-chain-access]').click();
          cy.get(`[name=team-${teamId0}]`).should('be.checked');
          cy.get(`[name=team-${teamId1}]`).should('not.be.checked');

          // Test clickability of the whole row. Select the first td, because
          // Cypress apparently clicks the middle of the selection, which is
          // the team link in this case.
          cy.get(`[name=team-${teamId0}]`).parents('tr').get('td').first().click();
          cy.get(`[name=team-${teamId0}]`).should('not.be.checked');
          cy.get(`[name=team-${teamId0}]`).parents('tr').get('td').first().click();
          cy.get(`[name=team-${teamId0}]`).should('be.checked');
        });
      });

      // Check that the first team sees the chain.
      cy.login('competitor0');
      cy.visit(`/${COMPETITION}/task/`);
      cy.contains("some chain name").should('exist');

      // Check that the second team does see the chain.
      cy.login('competitor1');
      cy.visit(`/${COMPETITION}/task/`);
      cy.contains("some chain name").should('not.exist');
    });
  });

  it("test adding or deleting a team while editing the access rights", () => {
    const COMPETITION = 'individual_competition_without_categories';
    const CHAIN = { numTasks: 3, position: 50, name: "some chain name", restrictedAccess: true };

    cy.login('moderator0');
    cy.setlang('en');
    cy.visit(`/${COMPETITION}/chain/tasks/`);
    cy.createChain(COMPETITION, CHAIN).then((chainJson) => {
      const chainId = chainJson['chain_id'];
      cy.visit(`/${COMPETITION}/chain/${chainId}/`);
      cy.get('input[name=restricted_access]').should('be.checked');
      cy.contains("Chain visibility").should('exist');
      cy.contains("No participants yet.").should('exist');

      // Create two teams.
      cy.createIndividualTeam(COMPETITION, 'competitor0', { category: 1 }).then((teamId0) => {
        cy.createIndividualTeam(COMPETITION, 'competitor1', { category: 2 }).then((teamId1) => {
          cy.reload();
          cy.contains("No participants yet.").should('not.exist');
          cy.get('#chain-access-table th').should('have.length', 2); // Team, checkbox.
          cy.get('#chain-access-table input[type=checkbox]').should('have.length', 2);
          cy.get(`[name=team-${teamId0}]`).should('not.be.checked');
          cy.get(`[name=team-${teamId1}]`).should('not.be.checked');

          // Check both, but add another team before submitting.
          cy.get(`[name=team-${teamId0}]`).myCheck();
          cy.get(`[name=team-${teamId1}]`).myCheck();
          cy.get(`[name=team-${teamId0}]`).should('be.checked');
          cy.get(`[name=team-${teamId1}]`).should('be.checked');

          cy.createIndividualTeam(COMPETITION, 'competitor2', { category: 3 }).then((teamId2) => {
            cy.get('[data-cy=change-chain-access]').click();

            cy.get(`[name=team-${teamId0}]`).should('be.checked');
            cy.get(`[name=team-${teamId1}]`).should('be.checked');
            cy.get(`[name=team-${teamId2}]`).should('not.be.checked');

            // Test unchecking first and second and checking third, while removing second and third.
            cy.get(`[name=team-${teamId0}]`).myUncheck();
            cy.get(`[name=team-${teamId1}]`).myUncheck();
            cy.get(`[name=team-${teamId2}]`).myCheck();
            cy.deleteTeams(COMPETITION, [teamId1, teamId2]);

            cy.get('[data-cy=change-chain-access]').click();
            cy.get(`[name=team-${teamId0}]`).should('not.be.checked');
          });
        });
      });
    });
  });

  it("test that users have no access to restricted chains", () => {
    const COMPETITION = 'individual_competition_without_categories';
    const CHAIN = { numTasks: 3, position: 50, name: "some chain name", restrictedAccess: true };
    cy.login('moderator0'); // For creating ctasks.
    cy.createChain(COMPETITION, CHAIN).then((chainJson) => {
      cy.createIndividualTeam(COMPETITION, 'competitor0');
      cy.login('competitor0');
      cy.expectNotFound(`/${COMPETITION}/task/${chainJson['ctask_ids'][0]}/`);
    });
  });

  it("test that users have access to restricted chains, given explicit rights", () => {
    const COMPETITION = 'individual_competition_without_categories';
    const CHAIN = { numTasks: 3, position: 50, name: "some chain name", restrictedAccess: true };
    cy.login('moderator0'); // For creating ctasks.
    cy.createChain(COMPETITION, CHAIN).then((chainJson) => {
      const options = { chainAccess: [chainJson['chain_id']] };
      cy.createIndividualTeam(COMPETITION, 'competitor0', options);
      cy.login('competitor0');
      cy.visit(`/${COMPETITION}/task/${chainJson['ctask_ids'][0]}/`);
      cy.contains("some chain name #1").should('exist');
    });
  });
});
