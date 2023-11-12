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
  restrictedAccess: false,
};

const CREATE_INDIVIDUAL_TEAM_DEFAULTS = {
  category: 0,
  chainAccess: [],
};

function _applyDefaults(options, defaults) {
  options = options || {};
  const unknownOptions = _.omit(options, Object.keys(defaults));
  if (!_.isEmpty(unknownOptions)) {
    throw new Error(`Unknown option(s): ${unknownOptions}`);
  }
  options = _.defaults({}, options, defaults);
  return options
}

/// Returns {ctask_ids: [ids...]}.
function createCTasks(competition, numTasks, textFormat, commentFormat) {
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
  options = _applyDefaults(options, CREATE_CHAIN_DEFAULTS);

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
      'restricted-access': options.restrictedAccess,
    }
  }).then((response) => {
    return response.body;
  });
}


/// Create a team. Returns team_id.
function createIndividualTeam(competition, username, options) {
  options = _applyDefaults(options, CREATE_INDIVIDUAL_TEAM_DEFAULTS);

  return cy.request({
    method: 'POST',
    url: `/${competition}/test/create_team/`,
    form: true,
    body: JSON.stringify({
      'name': username,
      'member-usernames': [username],
      'category': options.category,
      'chain-access': options.chainAccess,
    }),
  }).then((response) => {
    return response.body;
  });
}


/// Delete teams, given their IDs.
function deleteTeams(competition, teamIds) {
  return cy.request({
    method: 'POST',
    url: `/${competition}/test/delete_teams/`,
    form: true,
    body: JSON.stringify(teamIds),
  });
}

Cypress.Commands.add('createCTasks', createCTasks);
Cypress.Commands.add('createChain', createChain);
Cypress.Commands.add('createIndividualTeam', createIndividualTeam);
Cypress.Commands.add('deleteTeams', deleteTeams);
