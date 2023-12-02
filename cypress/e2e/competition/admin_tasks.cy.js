describe("test adding a new task", () => {
  before(() => {
    cy.resetdb();
    cy.request({ method: 'POST', url: '/competition/test/fill/' });
  });

  beforeEach(() => {
    cy.login('moderator0');
    cy.setlang('en');
  });

  it("test the default values and the required fields", () => {
    cy.visit('/competition_with_default_max_submissions_2/task/new/');
    cy.get('textarea').should('have.length', 2); // Text + comment.
    cy.get('#content input').should('have.length', 4); // CSRF + descriptor + max_score + max_submissions.
    cy.get('#id_descriptor').should('have.value', "");
    cy.get('#id_max_score').should('have.value', "1");
    cy.get('#id_max_submissions').should('have.value', "2"); // Must use competition.default_max_submissions!
    cy.get('#id_text').should('have.value', "");
    cy.get('#id_comment').should('have.value', "");

    cy.get('#id_descriptor').clear();
    cy.get('#id_max_score').clear();
    cy.get('#id_max_submissions').clear();
    cy.get('#id_text').clear();
    cy.get('#id_comment').clear();
    cy.get('#id_descriptor').type('{enter}'); // Submit.

    cy.get('#id_descriptor').requiredFieldError();
    cy.get('#id_max_score').requiredFieldError();
    cy.get('#id_max_submissions').requiredFieldError();
    cy.get('#id_text').requiredFieldError();
  });

  it("test the form remembers entered values", () => {
    cy.visit('/public_competition/task/new/');
    // Fill out everything except `descriptor`.
    cy.get('#id_descriptor').should('have.value', "");
    cy.get('#id_max_score').clear().type("100");
    cy.get('#id_max_submissions').clear().type("200");
    cy.get('#id_text').clear().type("dummy text");
    cy.get('#id_comment').clear().type("dummy comment");
    cy.get('#id_descriptor').type('{enter}'); // Submit.

    // Test all values are kept.
    cy.get('#id_descriptor').requiredFieldError();
    cy.get('#id_descriptor').should('have.value', "");
    cy.get('#id_max_score').should('have.value', "100");
    cy.get('#id_max_submissions').should('have.value', "200");
    cy.get('#id_text').should('have.value', "dummy text");
    cy.get('#id_comment').should('have.value', "dummy comment");

    // Now test the descriptor is saved by erasing id_text.
    cy.get('#id_text').clear();
    cy.get('#id_descriptor').clear().type("300{enter}");

    cy.get('#id_text').requiredFieldError();
    cy.get('#id_descriptor').should('have.value', "300");
    cy.get('#id_max_score').should('have.value', "100");
    cy.get('#id_max_submissions').should('have.value', "200");
    cy.get('#id_text').should('have.value', "");
    cy.get('#id_comment').should('have.value', "dummy comment");
  });

  it("test the add task form and the primary submit button", () => {
    cy.visit('/competition_with_default_max_submissions_2/task/new/');
    cy.get('#id_descriptor').type("123");
    cy.get('#id_max_score').clear().type("10");
    cy.get('#id_max_submissions').clear().type("15");

    // Test the text preview.
    cy.get('#id_text').clear().type("What is 100 + 23?{ctrl+M}");
    cy.get('#form-ctask-text').contains("What is 100 + 23?");
    cy.get('#id_text').type(" Hello.");
    cy.get('button[data-source="id_text"]').click();
    cy.get('#form-ctask-text').contains("What is 100 + 23? Hello.");

    // Test the comment preview.
    cy.get('#id_comment').clear().type("A comment.{ctrl+M}");
    cy.get('#form-ctask-comment').contains("A comment.");
    cy.get('#id_comment').type(" Another comment.");
    cy.get('button[data-source="id_comment"]').click();
    cy.get('#form-ctask-comment').contains("A comment. Another comment.");

    // Test the primary submit button (save and stay).
    cy.get('[data-cy="submit-primary"]').contains("Submit");
    cy.get('[data-cy="submit-primary"]').click();
    const regex = /^\/competition_with_default_max_submissions_2\/task\/\d+\/edit\/$/;
    cy.location('pathname').should('match', regex);
    cy.get('[data-cy="submit-primary"]').contains("Save changes");
    cy.get('#id_descriptor').should('have.value', "123");
    cy.get('#id_max_score').should('have.value', "10");
    cy.get('#id_max_submissions').should('have.value', "15");
    cy.get('#id_text').should('have.value', "What is 100 + 23? Hello.");
    cy.get('#id_comment').should('have.value', "A comment. Another comment.");
    cy.get('[data-cy="go-to-problem"]').click(); // Go to the (non-admin) task detail page.
    cy.get('#content .mc').contains("What is 100 + 23? Hello.");
  });

  it("test adding a task with the submit-and-new button", () => {
    cy.visit('/competition_with_default_max_submissions_2/task/new/');
    cy.get('#id_descriptor').type("123");
    cy.get('#id_max_score').clear().type("10");
    cy.get('#id_max_submissions').clear().type("15");
    cy.get('#id_text').clear().type("Text submit-and-new.");
    cy.get('#id_comment').clear().type("Comment submit-and-new.");
    cy.get('[data-cy="submit-and-new"]').click();
    cy.location('pathname').should('eq', '/competition_with_default_max_submissions_2/task/new/');
    cy.get('#id_descriptor').should('have.value', "");
    cy.get('#id_max_score').should('have.value', "1");
    cy.get('#id_max_submissions').should('have.value', "2");
    cy.get('#id_text').should('have.value', "");
    cy.get('#id_comment').should('have.value', "");
    cy.visit('/competition_with_default_max_submissions_2/chain/tasks/');
    cy.get('#cchain-unused-ctasks-table tr:last-child').contains("Text submit-and-new.");
    cy.get('#cchain-unused-ctasks-table tr:last-child').contains("Comment submit-and-new.");
  });

  it("test adding a task with the submit-and-return button", () => {
    cy.visit('/public_competition/task/new/');
    cy.get('#id_descriptor').type("123");
    cy.get('#id_max_score').clear().type("10");
    cy.get('#id_text').clear().type("Text submit-and-return.");
    cy.get('#id_comment').clear().type("Comment submit-and-return.");
    cy.get('[data-cy="submit-and-return"]').click();
    cy.location('pathname').should('eq', '/public_competition/chain/tasks/');
    cy.get('#cchain-unused-ctasks-table tr:last-child').contains("Text submit-and-return.");
    cy.get('#cchain-unused-ctasks-table tr:last-child').contains("Comment submit-and-return.");
  });
});
