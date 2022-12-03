Cypress.Commands.add('resetdb', () => {
  cy.request({
    method: 'POST',
    url: '/test/resetdb/',
  });
});
