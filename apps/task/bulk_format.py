from django.utils.translation import ugettext as _
from django.contrib.auth.models import User, Group

from folder.models import Folder
from permissions.constants import EDIT, PERMISSION_GROUPS

from task.models import DIFFICULTY_RATING_ATTRS, Task

from collections import defaultdict
import re

SEPARATION_EMPTY_LINES = 3  # Minimum number of separation lines between tasks.
VALUE_LENGTH_LIMIT = 10000

class BulkFormatError(Exception):
    pass

class ParseError(BulkFormatError):
    pass

class InvalidParameter(BulkFormatError):
    pass

class FolderNotFound(BulkFormatError):
    pass

class FolderNotEditable(BulkFormatError):
    pass

class InvalidValue(BulkFormatError):
    pass

class UserNotFound(BulkFormatError):
    pass

class GroupNotFound(BulkFormatError):
    pass

class UnknownVariable(BulkFormatError):
    pass

class CyclicDependency(BulkFormatError):
    pass

class ValueTooLong(BulkFormatError):
    pass


SOLUTION_SETTINGS_MAPPING = {
    'ALWAYS': Task.SOLUTIONS_VISIBLE,
    'IF_SOLVED': Task.SOLUTIONS_VISIBLE_IF_ACCEPTED,
    'EXPLICIT': Task.SOLUTIONS_NOT_VISIBLE,
}


class PrefetchData(object):
    def __init__(self):
        self.user_names = []
        self.group_names = []
        self.folder_ids = []

        self.users = None
        self.groups = None
        self.folders = None

    def prefetch(self, user):
        # Users.
        users = User.objects.filter(username__in=set(self.user_names))
        self.users = {x.username: x for x in users}

        # Groups.
        group_names = set([x.lower() for x in self.group_names])
        groups = Group.objects.filter(name__in=group_names)
        self.groups = {x.name.lower(): x for x in groups}

        # Folders.
        folders = Folder.objects.for_user(user, EDIT) \
                .filter(id__in=set(self.folder_ids))
        self.folders = {x.id: x for x in folders}



class TaskInfo(object):
    def __init__(self, json, template_data):
        self.json = json
        self.template_data = template_data



class InternalTaskInfo(object):
    def __init__(self, text, variables, permissions):
        self.text = text
        self.variables = variables
        self.permissions = list(permissions)  # Copy.
        self.json = None

    def init_json(self, prefetch):
        """Add initial values to json and add db requests to prefetch object.

        It is assumed that all the non-db checks have been performed."""
        variables = self.variables
        self.json = {
            'hidden': bool(int(variables['HIDDEN'] or False)),
            'name': variables['NAME'],
            'source': variables['SOURCE'],
            # 'solution_settings': SOLUTION_SETTINGS_MAPPING[
            #         variables['SOLUTION_SETTINGS'].upper()],
            # 'prerequisites': variables['PREREQUISITES'],
            '_content': self.text,
            '_difficulty': int(variables['DIFFICULTY'] or 0),
            '_folder_id': int(variables['FOLDER_ID'] or 0),
            '_folder_position': int(variables['FOLDER_POSITION'] or 0),
            '_tags': variables['TAGS'],
        }
        prefetch.user_names.append(variables['AUTHOR'])
        prefetch.folder_ids.append(self.json['_folder_id'])

    def check_and_finalize(self, prefetch):
        """Do db-related checks and finalize all fields."""
        var = self.variables
        template_data = {}

        # Author.
        author = prefetch.users.get(var['AUTHOR'], None)
        if not author:
            raise UserNotFound(_(u"User \"%s\" not found.") % var['AUTHOR'])
        self.json['author_id'] = author.id
        template_data['author'] = author

        # Folder.
        folder_id = self.json['_folder_id']
        if folder_id and folder_id not in prefetch.folders:
            msg = _("Folder #%d does not exist or no edit permission.")
            raise FolderNotFound(msg % folder_id)
        template_data['folder'] = prefetch.folders.get(folder_id)

        # Permissions and groups.
        perm_groups = defaultdict(list)
        perm_group_ids = defaultdict(list)
        for perm, group_name in self.permissions:
            try:
                group = prefetch.groups[group_name.lower()]
                perm_groups[perm].append(group)

                # Ahh, keys in JSON must be a string.
                perm_group_ids[str(perm)].append(group.id)
            except KeyError:
                raise GroupNotFound(
                        _(u"User or group \"%s\" not found.") % group_name)
        # Sort to be make unittests simpler.
        self.json['_permissions'] = {perm_id: sorted(ids) \
                for perm_id, ids in perm_group_ids.iteritems()}
        template_data['groups'] = prefetch.groups
        template_data['permissions'] = dict(perm_groups)

        return TaskInfo(self.json, template_data)





def _precheck_task_var_value(var, value, prefetch):
    """Helper function for parse_bulk.

    Raises an exception if the value is invalid."""

    try:
        int(value)
        is_int = True
    except:
        is_int = False

    if var in ['AUTHOR', 'NAME']:
        if not value:
            raise InvalidValue(_("Expected a non-empty string."))
    elif var == 'DIFFICULTY' and value.strip():
        maxd = DIFFICULTY_RATING_ATTRS['range'] - 1
        if not (is_int and 0 <= int(value) <= maxd):
            msg = _("Expected an integer between 0 and %d, inclusive.") % maxd
            raise InvalidValue(msg)
    elif var == 'FOLDER_ID' and value.strip():
        if not is_int or int(value) < 0:
            raise InvalidValue(
                    _("Expected a nonnegative integer or an empty string."))
        prefetch.folder_ids.append(int(value))
    elif var == 'FOLDER_POSITION':
        if value.strip() and not is_int:
            raise InvalidValue(_("Expected an integer or an empty string."))
    elif var == 'HIDDEN':
        if value.strip() not in ['0', '1']:
            raise InvalidValue(_("Expected 0 or 1."))
    # elif var == 'SOLUTION_SETTINGS':
    #     if value.upper() not in SOLUTION_SETTINGS_MAPPING:
    #         raise InvalidValue(_("Invalid value."))
    # elif var == 'PREREQUISITES':
    #     if not re.match('^(CHAIN|\d+\s*(,\s*\d+\s*)*|)$', value):
    #         raise InvalidValue(_("Invalid value."))


# Internal.
def split_expression(s):
    """Split @{xyz} parts from the expression s and return list of (is_var,
    value) pairs. Returns [(False, str(s))] if s is an integer."""
    if isinstance(s, (int, long)):
        return [(False, str(s))]

    result = []
    current = []

    k = 0
    while k < len(s):
        if k < len(s) - 1 and s[k] == '\\':
            current.append(s[k + 1])
            k += 2
            continue
        if s[k:k + 2] != '@{':
            current.append(s[k])
            k += 1
            continue
        if current:
            result.append((False, u''.join(current)))
            current = []
        end = s.find('}', k + 2)
        if end == -1:
            raise ParseError(_("Missing a '}' brace."))
        inner = s[k + 2:end]
        if inner.strip():
            result.append((True, inner.strip()))
        else:
            result.append((False, inner))
        k = end + 1

    if current:
        result.append((False, u''.join(current)))
    return result


# Internal.
def parse_variables(variables):
    """Helper function for parse_bulk.

    Returns dict {variable name: variable value}.
    """

    # Recursively traverse variables ang generate their final values.
    values = {}
    assert all(key == key.upper() for key in variables.keys())

    def _parse_monkey(monkey):
        """Parse @{...}. Currently we only support @{var} and @{factor*var}."""
        if '*' in monkey:
            factor, var = monkey.split('*', 1)
            try:
                return str(int(factor) * int(_generate(var)))
            except ValueError:
                raise BulkFormatError(_("Expected @{factor*variable-name}."))
        return _generate(monkey)

    def _generate(var):
        value = values.get(var, None)
        if value == -1:  # Gray node.
            msg = _(u"Cyclic dependency detected for the variable \"%s\".") % var
            raise CyclicDependency(msg)
        if value:
            return value

        values[var] = -1  # Gray node.
        result = []
        total = 0
        if var not in variables:
            raise UnknownVariable(_("Unknown variable name:") + " " + var)
        for is_var, part in split_expression(variables[var]):
            if is_var:
                result.append(_parse_monkey(part.upper()))
            else:
                result.append(part)
            total += len(result[-1])
            if total > VALUE_LENGTH_LIMIT:
                msg = _(u"Value of the variable \"%s\" too long.") % var
                raise ValueTooLong(msg)
        values[var] = u''.join(result)
        return values[var]


    for var in variables:
        _generate(var)

    return values


# Internal.
def parse_add_perm(input):
    """Parse @ADD_PERM parameters, whose format is
    "group[+group...] perm[+perm...]".

    Returns the list of pairs (permission type, group name)."""
    parameters = input.split()
    if len(parameters) != 2:
        raise InvalidParameter(_("Invalid parameter count."))

    # Split by +, strip whitespace and remove empty values.
    groups = [x.strip() for x in parameters[0].split('+') if x.strip()]
    permissions = [x.strip() for x in parameters[1].split('+') if x.strip()]

    result = []
    for permission in permissions:
        perms = PERMISSION_GROUPS.get(permission.lower(), None)
        if perms is None:
            raise InvalidParameter(_("Unrecognized permission name."))
        for perm in perms:
            for group in groups:
                result.append((perm, group))
    return result


def parse_bulk(user, full_content):
    """Parse bulk data and prepare for create_tasks_from_json.

    TODO: format

    Returns list of dictionaries describing the tasks, compatible with
    create_tasks_from_json.
    """
    # TODO: prerequisites
    # TODO: CHAIN
    # TODO: add an option to automatically create missing folders

    # Default values
    variables = {
        # Fields
        'AUTHOR': user.username,
        'HIDDEN': 0,
        'NAME': "",
        # 'SOLUTION_SETTINGS': 'ALWAYS',
        'SOURCE': "",

        # Values with some logic (that have an underscore in the name in json).
        'DIFFICULTY': 0,
        'FOLDER_ID': 0,
        'FOLDER_POSITION': 0,
        'TAGS': "",
        # 'PREREQUISITES': '',

        # Built-in values.
        'COUNTER': 1,
        'TOTAL_COUNTER': 1,
    }

    empty_counter = 0
    content = []    # Task lines.
    task_infos = []
    current_perms = []  # List of pairs (permission type, group name).

    def _prepare_task_info(text):
        var_values = parse_variables(variables)

        for var, value in var_values.iteritems():
            # Immediately check for trivial errors.
            try:
                _precheck_task_var_value(var, value, prefetch)
            except BulkFormatError as e:
                msg = (u"{} \"{}\"=\"{}\"<br>{}".format(
                    _("Invalid variable:"), var, value, e.message))
                raise type(e)(msg)

        # if var_values['PREREQUISITES'].strip() and \
        #         var_values['SOLUTION_SETTINGS'] == 'ALWAYS':
        #     raise ParseError(_(
        #             "If prerequisites are used, SOLUTION_SETTINGS "
        #             "cannot be set to ALWAYS."))
        return InternalTaskInfo(text, var_values, current_perms)


    def _line_error(message):
        return u"{} {}<br>{}".format(
                _("Error at line number %d:") % line_number, line, message)


    # Parse and check for any errors.
    prefetch = PrefetchData()
    lines = full_content.splitlines(True)
    lines.extend(['\n'] * SEPARATION_EMPTY_LINES)
    for line_number, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            content.append(line)
            empty_counter += 1
            if empty_counter == SEPARATION_EMPTY_LINES:  # Okay, we have a task.
                text = u''.join(content).strip()
                if not text:
                    continue  # False alarm.

                empty_counter = 0
                try:
                    task_infos.append(_prepare_task_info(text))
                except BulkFormatError as e:
                    prefix = _("Parsing error for the task #%d:") \
                            % variables['TOTAL_COUNTER']
                    msg = u'{}<br><br>{}<br><br><div class="tb-error">{}</div>'
                    raise type(e)(msg.format(prefix, text, e.message))
                variables['COUNTER'] += 1
                variables['TOTAL_COUNTER'] += 1
                content = []
            continue

        empty_counter = 0

        if stripped[0] == '%':
            pass  # Yes, we set empty_counter to 0, deliberately.
        elif re.match(r'^@\w+\s*=', stripped):
            var, value = stripped.split('=', 1)
            variables[var[1:].strip().upper()] = value.strip()
        elif stripped == '@RESET_COUNTER':
            variables['COUNTER'] = 1
        elif stripped == '@CLEAR_PERMS':
            current_perms = []
        elif stripped.startswith('@ADD_PERM '):
            try:
                new_perms = parse_add_perm(stripped[10:])
                current_perms.extend(new_perms)
                prefetch.group_names.extend([name for t, name in new_perms])
            except ParseError as e:
                raise type(e)(_line_error(e.message))
        elif stripped[0] == '@':
            raise ParseError(_line_error(_("Unknown command.")))
        else:
            content.append(line)

    for task_info in task_infos:
        task_info.init_json(prefetch)

    prefetch.prefetch(user)
    result = []
    for k, task_info in enumerate(task_infos):
        try:
            result.append(task_info.check_and_finalize(prefetch))
        except BulkFormatError as e:
            prefix = _("Invalid value(s) for the task #%d:") % (k + 1)
            msg = u'{}<br><br>{}<br><br><div class="tb-error">{}</div>'.format(
                    prefix, text, e.message)
            raise type(e)(msg)

    return result
