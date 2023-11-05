describe("test sign in and account registration", () => {
  beforeEach(() => {
    cy.resetdb();
    cy.request({ method: 'POST', url: '/competition/test/fill/' });
    cy.setlang('en');
    cy.visit('/public_competition/registration/');
  });

  it("test that sign-in leads to the team registration page", () => {
    cy.get('#id_username').type("competitor0");
    cy.get('#id_password').type("a");
    cy.get('[data-cy="login"] [type="submit"]').click();

    cy.location('pathname').should('eq', '/public_competition/registration/');
    cy.get('#sidebar').contains("Hello, competitor0!");
  });

  it("test that a failed sign-in still remembers the target URL", () => {
    cy.get('#id_username').type("competitor0");
    cy.get('#id_password').type("wrong_password");
    cy.get('[data-cy="login"] [type="submit"]').click();

    cy.location('pathname').should('eq', '/accounts/login/');
    cy.get('#id_username').should('have.value', "competitor0");
    cy.get('#id_password').type("a");
    cy.get('[data-cy="login"] [type="submit"]').click();

    cy.location('pathname').should('eq', '/public_competition/registration/');
    cy.get('#sidebar').contains("Hello, competitor0!");
  });

  it("test account registration", () => {
    cy.get('[data-cy=registration] [name=username]').type("someusername");
    cy.get('[data-cy=registration] [name=email]').type("dummy@skoljka.org");
    cy.get('[data-cy=registration] [name=password1]').type("abc");
    cy.get('[data-cy=registration] [name=password2]').type("abc");
    cy.get('[data-cy=registration] [type=checkbox]').click();
    cy.get('[data-cy=registration] [type=submit]').click();

    cy.location('pathname').should('eq', '/accounts/register/complete/');
    cy.location('search').should('match', /^\?email=.*$/);
    cy.contains("Thank you for signing up!");
  });
});


describe("test registering for an individual competition", () => {
  beforeEach(() => {
    cy.resetdb();
    cy.request({ method: 'POST', url: '/competition/test/fill/' });
    cy.setlang('en');
    cy.login('competitor0');
  });

  it("test without team categories", () => {
    cy.visit('/individual_competition_without_categories/registration/');
    cy.contains("Please register to participate in the competition.");
    cy.get('form[data-cy=creg] input').should('have.length', 2); // Hidden + submit.
    cy.get('form[data-cy=creg] [data-cy=register]').click();
    cy.contains("Registration successful!");

    // Test that visiting the same page leads to the competition home page.
    cy.visit('/individual_competition_without_categories/registration/');
    cy.location('pathname').should('eq', '/individual_competition_without_categories/team/1/');
  });

  it("test with team categories and test changing the category", () => {
    cy.visit('/individual_competition_with_categories/registration/');
    cy.contains("Please register to participate in the competition.");
    // Hidden + submit + 3 categories.
    cy.get('form[data-cy=creg] input').should('have.length', 5);
    cy.get('form[data-cy=creg] label').contains("Green").click();
    cy.get('form[data-cy=creg] [data-cy=register]').click();
    cy.contains("Registration successful!");

    cy.get('a').contains("Scoreboard").click();
    cy.get('[data-cy=scoreboard] tr').should('have.length', 2);
    cy.get('[data-cy=scoreboard] tr').eq(1).contains("Green");
    cy.get('[data-cy=scoreboard] tr').eq(1).contains("competitor0");

    cy.get('a[data-cy=edit-participation]').click();
    // No more instructions, we already have a team.
    cy.get('.instructions').should('not.exist');
    cy.get('form[data-cy=creg] label').contains("Red").click();
    cy.get('form[data-cy=creg] [data-cy="submit-team-changes"]').click();

    cy.get('a').contains("Scoreboard").click();
    cy.get('[data-cy=scoreboard] tr').should('have.length', 2);
    cy.get('[data-cy=scoreboard] tr').eq(1).contains("Red");
    cy.get('[data-cy=scoreboard] tr').eq(1).contains("competitor0");
  });

  it("test with non-configurable team categories (i.e. only set by moderators)", () => {
    cy.visit('/individual_competition_with_nonconfigurable_categories/registration/');
    cy.get('form[data-cy=creg] [data-cy=register]').click();
    cy.visit('/individual_competition_with_nonconfigurable_categories/scoreboard/');
    cy.get('[data-cy=scoreboard] tr').eq(1).contains("Blue"); // Last category is the default.

    // Try to visit the team edit page.
    cy.contains("Team: competitor0").should('not.exist');
    cy.get('[data-cy=edit-team]').should('not.exist');
    cy.visit('/individual_competition_with_nonconfigurable_categories/registration/');
    cy.location('pathname').should('eq', '/individual_competition_with_nonconfigurable_categories/team/1/');
  });
});

describe("test registering for a team competition without categories", () => {
  beforeEach(() => {
    cy.resetdb();
    cy.request({ method: 'POST', url: '/competition/test/fill/' });
    cy.login('competitor0');
    cy.setlang('en');
    cy.visit('/public_competition/registration/');
  });

  it("test that the team name is required", () => {
    // Hidden + name + 2 per invitations (x2) + submit.
    cy.get('form[data-cy=creg] input').should('have.length', 7);
    cy.get('form[data-cy=creg] [data-cy=register]').click();
  });

  it("test creating a team with no extra members; test changing the name", () => {
    cy.get('#id_name').type("TeamName{enter}");
    cy.contains("Team successfully registered!");
    cy.contains("Team: TeamName");
    cy.get('[data-cy=edit-participation]').should('not.exist'); // For individual competitions.

    // Test changing the name.
    cy.get('a').contains("TeamName").click();
    cy.get('#id_name').clear();
    cy.get('#id_name').type("NewTeamName{enter}");
    cy.contains("Changes saved!");
    cy.contains("Team: NewTeamName");
  });

  it("test creating a team with two name-only members", () => {
    // Create a team with no extra members.
    cy.get('#id_name').type("TeamName");
    cy.get('#member2_manual').type("Member2");
    cy.get('#member3_manual').type("Member3{enter}");
    cy.contains("Team successfully registered!");
    cy.get('a').contains("TeamName").click();
    cy.get('#member2_manual').should('have.value', "Member2");
    cy.get('#member2_manual').should('have.class', 'creg-invitation-accepted');
    cy.get('#member3_manual').should('have.value', "Member3");
    cy.get('#member3_manual').should('have.class', 'creg-invitation-accepted');
  });

  it("test editing name-only members, starting with no extra members", () => {
    // Create a team with no extra members.
    cy.get('#id_name').type("TeamName{enter}");
    cy.contains("Team successfully registered!");

    // Test adding a name-only member.
    cy.get('a').contains("TeamName").click();
    cy.get('#member2_manual').type("MemberName{enter}");
    cy.contains("Changes saved!");
    cy.get('#member2_manual').should('have.value', "MemberName");
    cy.get('#member2_manual').should('have.class', 'creg-invitation-accepted');

    // Test removing the member.
    cy.get('#member2_manual').clear();
    cy.get('#member2_manual').type("{enter}");
    cy.contains("Changes saved!");
    cy.get('#member2_manual').should('have.value', "");
    cy.get('#member2_manual').should('not.have.class', 'creg-invitation-accepted');

    // Test adding a name-only member as the 3rd member.
    cy.get('#member3_manual').type("OtherMemberName{enter}");
    cy.contains("Changes saved!");
    cy.get('#member2_manual').should('have.value', "OtherMemberName");
    cy.get('#member2_manual').should('have.class', 'creg-invitation-accepted');
    cy.get('#member3_manual').should('have.value', "");
    cy.get('#member3_manual').should('not.have.class', 'creg-invitation-accepted');

    // Test adding both name-only members.
    cy.get('#member2_manual').clear();
    cy.get('#member2_manual').type("Member2");
    cy.get('#member3_manual').clear();
    cy.get('#member3_manual').type("Member3{enter}");
    cy.get('#member2_manual').should('have.value', "Member2");
    cy.get('#member2_manual').should('have.class', 'creg-invitation-accepted');
    cy.get('#member3_manual').should('have.value', "Member3");
    cy.get('#member3_manual').should('have.class', 'creg-invitation-accepted');
  });

  it("test creating a team with one invited member; test accepting and deleting", () => {
    // Submit the invitation.
    cy.get('.creg-table-row[data-index=2] button').contains("Invite user").click();
    cy.get('#member2_manual').should('be.disabled');
    cy.get('[name=member2_username]').eq(1).type("compe");
    cy.get('.ac_results li').contains("competitor2").click(); // Test autocomplete.
    cy.get('#id_name').type("TeamName{enter}");

    // Accept the invitation.
    cy.login('competitor2');
    cy.setlang('en');
    cy.visit('/public_competition/registration/');
    cy.get('[data-cy="invitations-table"] tr:nth-child(2)').then((tr) => {
      cy.wrap(tr).find('td:nth-child(1)').contains("TeamName");
      cy.wrap(tr).find('td:nth-child(2)').contains("competitor0");
      cy.wrap(tr).find('td:nth-child(3)').find('button').contains("Accept invitation").click();
    });
    // Note: For now, the non-authors don't have an option to leave the team, change the name etc.
    cy.contains("Team: TeamName");
    cy.get('[data-cy=team-member1] a').contains("competitor0");
    cy.get('[data-cy=team-member2] a').contains("competitor2");

    // Test the team form from the point of view of the author.
    cy.login('competitor0');
    cy.setlang('en');
    cy.visit('/public_competition/registration/');
    cy.get('#member2_manual').should('have.class', 'creg-invitation-accepted');
    cy.get('#member2_manual').should('be.disabled');

    // Test kicking out the member.
    cy.get('.creg-table-row[data-index=2] button').contains("Delete").click();
    cy.get('[data-cy=submit-team-changes]').click();
    cy.get('#member2_manual').should('not.be.disabled');
    cy.get('#member2_manual').should('have.value', "");

    // Test from the point of view of the member.
    cy.login('competitor2');
    cy.setlang('en');
    cy.visit('/public_competition/registration/');
    cy.contains("Team: TeamName").should('not.exist');
  });

  it("test inviting the same member twice", () => {
    // Submit the invitations.
    cy.get('.creg-table-row[data-index=3] button').contains("Invite user").click();
    cy.get('.creg-table-row[data-index=2] button').contains("Invite user").click();
    // Note: We do not (yet) delete old autocomplete divs, so here we have to
    // manually select which one we target.
    cy.get('[name=member2_username]').eq(1).type("compe");
    cy.get('.ac_results').eq(0).find('li').contains("competitor5").click(); // Test autocomplete.
    cy.get('[name=member3_username]').eq(1).type("compe");
    cy.get('.ac_results').eq(1).find('li').contains("competitor5").click({ force: true }); // Test autocomplete.
    cy.get('#id_name').type("TeamName{enter}");

    // Test one of them was ignored.
    cy.get('a').contains("TeamName").click();
    cy.get('.creg-table-row[data-index=2] button').contains("Cancel");
    cy.get('.creg-table-row[data-index=3] button').contains("Invite user");

    // Test that the invited user has only one invitation.
    cy.login('competitor5');
    cy.visit('/public_competition/registration/');
    cy.get('[data-cy="invitations-table"] tr').should('have.length', 2); // Header + 1 invitation.
  });

  it("test inviting two members", () => {
    // Submit the invitations.
    cy.get('.creg-table-row[data-index=2] button').contains("Invite user").click();
    cy.get('.creg-table-row[data-index=3] button').contains("Invite user").click();
    cy.get('[name=member2_username]').eq(1).type("competitor5");
    // Get rid of the autocomplete, so that we can type to member3_username.
    cy.get('#id_name').click();
    cy.get('[name=member3_username]').eq(1).type("competitor6");
    cy.get('#id_name').type("TeamName{enter}");

    cy.login('competitor5');
    cy.setlang('en');
    cy.visit('/public_competition/registration/');
    cy.get('[data-cy="invitations-table"]').find('button').contains("Accept invitation").click();

    cy.login('competitor6');
    cy.setlang('en');
    cy.visit('/public_competition/registration/');
    cy.get('[data-cy="invitations-table"]').find('button').contains("Accept invitation").click();

    // Note: For now, the non-authors don't have an option to leave the team, change the name etc.
    cy.contains("Team: TeamName");
    cy.get('[data-cy=team-member1] a').contains("competitor0");
    cy.get('[data-cy=team-member2] a').contains("competitor5");
    cy.get('[data-cy=team-member3] a').contains("competitor6");
  });

  it("test one name-only and one invited user", () => {
    cy.get('.creg-table-row[data-index=2] button').contains("Invite user").click();
    cy.get('[name=member2_username]').eq(1).type("competitor5");
    cy.get('#member3_manual').type("nameonly");
    cy.get('#id_name').type("TeamName{enter}");

    cy.login('competitor5');
    cy.setlang('en');
    cy.visit('/public_competition/registration/');
    cy.get('[data-cy="invitations-table"]').find('button').contains("Accept invitation").click();

    cy.get('[data-cy=team-member1] a').contains("competitor0");
    cy.get('[data-cy=team-member2] a').contains("competitor5");
    cy.get('[data-cy=team-member3]').find('a').should('not.exist');
    cy.get('[data-cy=team-member3]').contains("nameonly");
  });

  it("test cancel invite", () => {
    for (let i = 2; i <= 3; ++i) {
      const input = `#member${i}_manual`;
      const button = `.creg-table-row[data-index=${i}] button`;

      // Initial state.
      cy.get(input).should('not.be.disabled');
      cy.get(button).contains("Cancel").should('not.exist');
      cy.get(button).contains("Invite user").click(); // Should exist + click.

      // "Invite user" pressed.
      cy.get(input).should('be.disabled');
      cy.get(button).contains("Invite user").should('not.exist');
      cy.get(button).contains("Cancel").click(); // Should exist + click.

      // Back to the initial state.
      cy.get(input).should('not.be.disabled');
      cy.get(button).contains("Invite user"); // Should exist.
      cy.get(button).contains("Cancel").should('not.exist');
    }
  });
});

describe("test registering for a team competition with categories", () => {
  beforeEach(() => {
    cy.resetdb();
    cy.request({ method: 'POST', url: '/competition/test/fill/' });
    cy.login('competitor0');
    cy.setlang('en');
    cy.visit('/competition_with_categories/registration/');
  });

  it("test setting a category and inviting one member", () => {
    // Submit the invitations.
    cy.get('.creg-table-row[data-index=2] button').contains("Invite user").click();
    cy.get('[name=member2_username]').eq(1).type("competitor5");
    cy.get('label').contains("Green").click();
    cy.get('#id_name').type("TeamName{enter}");

    cy.login('competitor5');
    cy.setlang('en');
    cy.visit('/competition_with_categories/registration/');
    cy.get('[data-cy="invitations-table"]').find('button').contains("Accept invitation").click();

    // Note: For now, the non-authors don't have an option to leave the team, change the name etc.
    cy.contains("Team: TeamName");
    cy.get('[data-cy=team-member1] a').contains("competitor0");
    cy.get('[data-cy=team-member2] a').contains("competitor5");

    // Check the category.
    cy.visit('/competition_with_categories/scoreboard/');
    cy.get('[data-cy=scoreboard] .comp-my-team td').contains("Green");
  });
});
