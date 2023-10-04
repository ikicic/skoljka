import _ from 'lodash';

const UNLOCK_GRADUAL = 1;
// const UNLOCK_ALL = 2;

const CREATE_CHAIN_DEFAULTS = {
  name: "test chain",
  category: "test category",
  position: 100,
  bonus: +1,
  unlockMode: UNLOCK_GRADUAL,
  unlockMinutes: 0,
  numTasks: 0,
  textFormat: "task text #{}",
  commentFormat: "task comment #{}",
};

/// Returns {ctask_ids: [ids...]}.
function createTasks(competition, numTasks, textFormat, commentFormat) {
  return cy.request({
    method: 'POST',
    url: `/${competition}/test/create_ctasks/`,
    form: true,
    body: { 'num-tasks': numTasks, 'text-format': textFormat, 'comment-format': commentFormat },
  }).then((response) => {
    return response.body;
  });
}

/// Create a chain and ctasks in it. Returns {ctask_ids: [ids...], chain_id: ...}.
function createChain(competition, options) {
  options = options || {};
  const unknownOptions = _.omit(options, Object.keys(CREATE_CHAIN_DEFAULTS));
  if (!_.isEmpty(unknownOptions)) {
    throw new Error(`Unknown option(s): ${unknownOptions}`);
  }
  options = _.defaults({}, options, CREATE_CHAIN_DEFAULTS);

  return cy.request({
    method: 'POST',
    url: `/${competition}/test/create_chain/`,
    form: true,
    body: {
      'name': options.name,
      'category': options.category,
      'position': options.position,
      'bonus': options.bonus,
      'unlock-mode': options.unlockMode,
      'unlock-minutes': options.unlockMinutes,
      'num-tasks': options.numTasks,
      'text-format': options.textFormat,
      'comment-format': options.commentFormat,
    }
  }).then((response) => {
    return response.body;
  });
}

Cypress.Commands.add('createTasks', createTasks);
Cypress.Commands.add('createChain', createChain);
