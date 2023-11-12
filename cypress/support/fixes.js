/// A replacement for Cypress .check() which sometimes does not work.
function myCheck(subject) {
  if (subject.is(':checkbox') || subject.is(':radio')) {
    subject.prop('checked', true);
  } else {
    throw new Error(`Expected a checkbox or radio, got: ${subject}`);
  }
}

/// A replacement for Cypress .uncheck() which sometimes does not work.
function myUncheck(subject) {
  if (subject.is(':checkbox') || subject.is(':radio')) {
    subject.prop('checked', false);
  } else {
    throw new Error(`Expected a checkbox or radio, got: ${subject}`);
  }
}

Cypress.Commands.add('myCheck', { prevSubject: true }, myCheck);
Cypress.Commands.add('myUncheck', { prevSubject: true }, myUncheck);
