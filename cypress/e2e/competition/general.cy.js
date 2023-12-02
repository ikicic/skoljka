/**
 * \brief Compares the given url with the (pathname + search) part of the
 * location: /this/part/?and=5&get=10.
 */
function checkUrl(expectedUrl) {
  return cy.location().then((location) => {
    return location.pathname + location.search;
  }).should('eq', expectedUrl);
}

describe("test the course and competition redirects", () => {
  before(() => {
    cy.resetdb();
    cy.request({ method: 'POST', url: '/competition/test/fill/' });
  });

  it("test /competition/<id>/ redirects to /competition_name/ if the competition has url_path_prefix", () => {
    cy.visit('/competition/10001/task/');
    cy.location('pathname').should('eq', '/public_competition/task/');

    cy.visit('/competition/10001/task/?a=5&b=10');
    checkUrl('/public_competition/task/?a=5&b=10');
  });

  it("test /course/<id>/ redirects to /competition_name/ if the competition has url_path_prefix", () => {
    cy.visit('/course/10001/task/');
    cy.location('pathname').should('eq', '/public_competition/task/');

    cy.visit('/course/10001/task/?a=5&b=10');
    checkUrl('/public_competition/task/?a=5&b=10');
  });

  it("test /competition/<id>/ redirects to /course_name/ if the course has url_path_prefix", () => {
    cy.visit('/competition/10007/task/');
    cy.location('pathname').should('eq', '/individual_course_without_categories/task/');

    cy.visit('/competition/10007/task/?a=5&b=10');
    checkUrl('/individual_course_without_categories/task/?a=5&b=10');
  });

  it("test /course/<id>/ redirects to /course_name/ if the course has url_path_prefix", () => {
    cy.visit('/course/10007/task/');
    cy.location('pathname').should('eq', '/individual_course_without_categories/task/');

    cy.visit('/course/10007/task/?a=5&b=10');
    checkUrl('/individual_course_without_categories/task/?a=5&b=10');
  });

  it("test /competition/<id>/ redirects to /course/<id>/ if the course has no url_path_prefix", () => {
    cy.visit('/competition/10009/task/');
    cy.location('pathname').should('eq', '/course/10009/task/');

    cy.visit('/competition/10009/task/?a=5&b=10');
    checkUrl('/course/10009/task/?a=5&b=10');
  });

  it("test /course/<id>/ redirects to /competition/<id>/ if the competition has no url_path_prefix", () => {
    cy.visit('/course/10008/task/');
    cy.location('pathname').should('eq', '/competition/10008/task/');

    cy.visit('/course/10008/task/?a=5&b=10');
    checkUrl('/competition/10008/task/?a=5&b=10');
  });
});
