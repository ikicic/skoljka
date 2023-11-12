/// Visit a page and expect the 403 status code (forbidden).
function expectForbidden(url) {
  return cy.request({
    url: url,
    failOnStatusCode: false,
  }).its('status').should('equal', 403);
}

/// Visit a page and expect the 404 status code (not found).
function expectNotFound(url) {
  return cy.request({
    url: url,
    failOnStatusCode: false,
  }).its('status').should('equal', 404);
}

/// Check that the given form field reported a value error.
/// Returns the text of the error.
function fieldError(subject) {
  // For bootstrap_toolkit.
  return cy.wrap(subject).parents('.control-group').then((parent) => {
    expect(parent).to.have.class('error');
    return cy.wrap(parent).find('.help-block, .help-inline.error').invoke('text');
  });
}

/// Check that the form reported an error that the field is required.
function requiredFieldError(subject) {
  return fieldError(subject).should('contain', "This field is required.");
}

/// Sign in the given username via the test API, without the password and CSRF.
function login(username) {
  cy.request({
    method: 'POST',
    url: '/test/login/',
    form: true,
    body: { username: username },
  });
}

/// Sign the user out.
function logout() {
  cy.request({ method: 'POST', url: '/test/logout/' });
}

/// Reset the (test) database.
function resetdb() {
  cy.request({
    method: 'POST',
    url: '/test/resetdb/',
  });
}

/// Set a language, given its short code (e.g. 'en').
function setlang(lang) {
  cy.request({
    method: 'POST',
    url: '/test/setlang/',
    form: true,
    body: { language: lang },
  });
}

Cypress.Commands.add('expectForbidden', expectForbidden);
Cypress.Commands.add('expectNotFound', expectNotFound);
Cypress.Commands.add('fieldError', { prevSubject: true }, fieldError);
Cypress.Commands.add('requiredFieldError', { prevSubject: true }, requiredFieldError);
Cypress.Commands.add('login', login);
Cypress.Commands.add('logout', logout);
Cypress.Commands.add('resetdb', resetdb);
Cypress.Commands.add('setlang', setlang);
