describe("test the course and the competition list", () => {
  before(() => {
    cy.resetdb();
    cy.request({ method: 'POST', url: '/competition/test/fill/' });
  });

  it("test the competition list (not signed in)", () => {
    cy.logout();
    cy.visit('/competition/');
    cy.get('#comp-list tr').should('have.length', 8); // Header + 7 courses.
    let k = 1;
    let l = 1;
    cy.get('#comp-list tr').eq(k++).contains("10010");
    cy.get('#comp-list tr').eq(k++).contains("10008");
    cy.get('#comp-list tr').eq(k++).contains("10006");
    cy.get('#comp-list tr').eq(k++).contains("10005");
    cy.get('#comp-list tr').eq(k++).contains("10004");
    cy.get('#comp-list tr').eq(k++).contains("10003");
    cy.get('#comp-list tr').eq(k++).contains("10001");
    cy.get('#comp-list tr').eq(l++).contains("Competition with default max submissions 2");
    cy.get('#comp-list tr').eq(l++).contains("Competition with no url path prefix");
    cy.get('#comp-list tr').eq(l++).contains("Individual competition with nonconfigurable categories");
    cy.get('#comp-list tr').eq(l++).contains("Individual competition without categories");
    cy.get('#comp-list tr').eq(l++).contains("Individual competition with categories");
    cy.get('#comp-list tr').eq(l++).contains("Competition with categories");
    cy.get('#comp-list tr').eq(l++).contains("Public competition");
  });

  it("test the competition list (signed in)", () => {
    cy.login('moderator0');
    cy.visit('/competition/');
    cy.get('#comp-list tr').should('have.length', 9); // Header + 8 courses.
    let k = 1;
    let l = 1;
    cy.get('#comp-list tr').eq(k++).contains("10010");
    cy.get('#comp-list tr').eq(k++).contains("10008");
    cy.get('#comp-list tr').eq(k++).contains("10006");
    cy.get('#comp-list tr').eq(k++).contains("10005");
    cy.get('#comp-list tr').eq(k++).contains("10004");
    cy.get('#comp-list tr').eq(k++).contains("10003");
    cy.get('#comp-list tr').eq(k++).contains("10002");
    cy.get('#comp-list tr').eq(k++).contains("10001");
    cy.get('#comp-list tr').eq(l++).contains("Competition with default max submissions 2");
    cy.get('#comp-list tr').eq(l++).contains("Competition with no url path prefix");
    cy.get('#comp-list tr').eq(l++).contains("Individual competition with nonconfigurable categories");
    cy.get('#comp-list tr').eq(l++).contains("Individual competition without categories");
    cy.get('#comp-list tr').eq(l++).contains("Individual competition with categories");
    cy.get('#comp-list tr').eq(l++).contains("Competition with categories");
    cy.get('#comp-list tr').eq(l++).contains("Hidden competition");
    cy.get('#comp-list tr').eq(l++).contains("Public competition");
  });

  it("test the course list", () => {
    cy.logout();
    cy.visit('/course/');
    cy.get('#comp-list tr').should('have.length', 3); // Header + 2 course.
    let k = 1;
    let l = 1;
    cy.get('#comp-list tr').eq(k++).contains("10009");
    cy.get('#comp-list tr').eq(k++).contains("10007");
    cy.get('#comp-list tr').eq(l++).contains("Course with no url path prefix");
    cy.get('#comp-list tr').eq(l++).contains("Individual course without categories");
  });
});
