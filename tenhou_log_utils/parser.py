"""Functionality to parse mjlog (XML) data"""
from __future__ import absolute_import
from __future__ import division

import logging
from tenhou_log_utils.io import ensure_unicode, unquote

_LG = logging.getLogger(__name__)

# TODO: Expose all parse_XX functions.


def _parse_str_list(val, type_):
    return [type_(val) for val in val.split(',')] if val else []


###############################################################################
def _parse_shuffle(attrib):
    return {
        'seed': attrib['seed'],
        'ref': attrib['ref'],
    }


###############################################################################
def _parse_game_mode(game_mode):
    _LG.debug('  Game Mode: %s', bin(game_mode))
    test = not bool(game_mode & 0x01)
    tokujou = bool((game_mode & 0x20) >> 5)
    joukyu = bool((game_mode & 0x80) >> 7)
    if tokujou and joukyu:
        table = 'tenhou'
    elif test:
        table = 'test'
    elif tokujou:
        table = 'tokujou'
    elif joukyu:
        table = 'joukyu'
    else:
        table = 'dan-i'
    mode = {
        'red': not bool((game_mode & 0x02) >> 1),
        'kui': not bool((game_mode & 0x04) >> 2),
        'ton-nan': bool((game_mode & 0x08) >> 3),
        'sanma': bool((game_mode & 0x10) >> 4),
        'soku': bool((game_mode & 0x40) >> 6),
    }
    return table, mode


def _parse_go(attrib):
    table, mode = _parse_game_mode(int(attrib['type']))
    number_ = int(attrib.get('lobby', '-1'))
    return {'table': table, 'mode': mode, 'num': number_}


###############################################################################
def _parse_resume(attrib):
    index = int(list(attrib.keys())[0][1])
    name = unquote(list(attrib.values())[0])
    return {'index': index, 'name': name}


def _parse_un(attrib):
    indices, names = [], []
    for key in ['n0', 'n1', 'n2', 'n3']:
        if key in attrib:
            indices.append(int(key[1]))
            names.append(unquote(attrib[key]))
    dans = _parse_str_list(attrib.get('dan', '-1,-1,-1,-1'), type_=int)
    rates = _parse_str_list(attrib['rate'], type_=float)
    sexes = _parse_str_list(attrib['sx'], type_=ensure_unicode)

    return [
        {'index': i, 'name': name, 'dan': dan, 'rate': rate, 'sex': sex}
        for i, name, dan, rate, sex in zip(indices, names, dans, rates, sexes)
    ]


################################################################################
def _parse_taikyoku(attrib):
    return {'oya': attrib['oya']}


###############################################################################
def _parse_score(data):
    return [score * 100 for score in _parse_str_list(data, type_=int)]


def _parse_init(attrib):
    seed = _parse_str_list(attrib['seed'], type_=int)
    scores = _parse_score(attrib['ten'])
    hands = [
        _parse_str_list(attrib[key], type_=int)
        for key in ['hai0', 'hai1', 'hai2', 'hai3'] if key in attrib
    ]
    return {
        'oya': attrib['oya'],
        'scores': scores,
        'hands': hands,
        'round': seed[0],
        'combo': seed[1],
        'reach': seed[2],
        'dices': seed[3:5],
        'dora_indicator': seed[5],
    }


###############################################################################
def _parse_draw(tag):
    player = ord(tag[0]) - ord('T')
    tile = int(tag[1:])
    return {'player': player, 'tile': tile}


###############################################################################
def _parse_discard(tag):
    player = ord(tag[0]) - ord('D')
    tile = int(tag[1:])
    return {'player': player, 'tile': tile}


###############################################################################
def _parse_shuntsu(meld):
    # Adopted from http://tenhou.net/img/tehai.js
    t = (meld & 0xfc00) >> 10
    r = t % 3
    t = t // 3
    t = 9 * (t // 7) + (t % 7)
    t *= 4
    h = [
        t + 4*0 + ((meld & 0x0018)>>3),
        t + 4*1 + ((meld & 0x0060)>>5),
        t + 4*2 + ((meld & 0x0180)>>7),
    ]
    if r == 1:
        h = [h[1], h[0], h[2]]
    elif r == 2:
        h = [h[2], h[0], h[1]]
    return h


def _parse_koutsu(meld):
    # Adopted from http://tenhou.net/img/tehai.js
    unused = (meld &0x0060) >> 5
    t = (meld & 0xfe00) >> 9
    r = t % 3
    t = t // 3
    t *= 4
    h = [t, t, t]
    if unused == 0:
        h[0] += 1
        h[1] += 2
        h[2] += 3
    elif unused == 1:
        h[0] += 0
        h[1] += 2
        h[2] += 3
    elif unused == 2:
        h[0] += 0
        h[1] += 1
        h[2] += 3
    elif unused == 3:
        h[0] += 0
        h[1] += 1
        h[2] += 2
    if r == 1:
        h = [h[1], h[0], h[2]]
    elif r == 2:
        h = [h[2], h[0], h[1]]
    kui = meld & 0x3
    if kui < 3:
        h = [h[2], h[0], h[1]]
    if kui < 2:
        h = [h[2], h[0], h[1]]
    return h


def _parse_kakan(meld):
    # Adopted from http://tenhou.net/img/tehai.js
    added = (meld & 0x0060) >> 5
    t = (meld & 0xFE00) >> 9
    r = t % 3
    t = t // 3
    t *= 4
    h = [t, t, t]
    if added == 0:
        h[0] += 1
        h[1] += 2
        h[2] += 3
    elif added == 1:
        h[0] += 0
        h[1] += 2
        h[2] += 3
    elif added == 2:
        h[0] += 0
        h[1] += 1
        h[2] += 3
    elif added == 3:
        h[0] += 0
        h[1] += 1
        h[2] += 2
    if r == 1:
        h = [h[1], h[0], h[2]]
    elif r == 2:
        h = [h[2], h[0], h[1]]
    kui = meld & 0x3
    if kui == 3:
        h = [t + added, h[0], h[1], h[2]]
    elif kui == 2:
        h = [h[1], t + added, h[0], h[2]]
    elif kui == 1:
        h = [h[2], h[1], t + added, h[0]]
    return h


def _parse_kan(meld):
    # Adopted from http://tenhou.net/img/tehai.js
    hai0 = (meld & 0xff00) >> 8
    kui = meld & 0x3
    if not kui:  # Ankan
        hai0 = (hai0 & ~3) +3
    t = (hai0 // 4) * 4
    h = [t, t, t]
    rem = hai0 % 4
    if rem == 0:
        h[0] += 1
        h[1] += 2
        h[2] += 3
    elif rem == 1:
        h[0] += 0
        h[1] += 2
        h[2] += 3
    elif rem == 2:
        h[0] += 0
        h[1] += 1
        h[2] += 3
    else:
        h[0] += 0
        h[1] += 1
        h[2] += 2
    if kui == 1:
        hai0, h[2] = h[2], hai0
    if kui == 2:
        hai0, h[0] = h[0], hai0
    return [hai0] + h if kui else h[:2]


def _parse_call(attrib):
    caller = int(attrib['who'])
    meld = int(attrib['m'])

    _LG.debug('  Meld: %s', bin(meld))
    if meld & (1 << 2):
        mentsu = _parse_shuntsu(meld)
        type_ = 'Chi'
    elif meld & (1 << 3):
        type_ = 'Pon'
        mentsu = _parse_koutsu(meld)
    elif meld & (1 << 4):
        type_ = 'KaKan'
        mentsu = _parse_kakan(meld)
    elif meld & (1 << 5):
        type_ = 'Nuki'
        mentsu = [meld >> 8]
    else:
        type_ = 'Kan'
        mentsu = _parse_kan(meld)
    callee = (caller + meld & 0x3) % 4  # Relative -> Absolute
    return {
        'caller': caller, 'callee': callee,
        'call_type': type_, 'mentsu': mentsu
    }


###############################################################################
def _parse_reach(attrib):
    who, step = int(attrib['who']), int(attrib['step'])
    if step > 2:
        raise NotImplementedError('Unexpected step value: {}'.format(attrib))

    result = {'player': who, 'step': step}
    # Old logs do not have ten values.
    if 'ten' in attrib:
        result['score'] = _parse_score(attrib['ten'])
    return result


################################################################################
def _nest_list(vals):
    if len(vals) % 2:
        raise RuntimeError('List with odd number of value was given.')
    return list(zip(vals[::2], vals[1::2]))


def _parse_ba(val):
    vals = _parse_str_list(val, type_=int)
    return {'combo': vals[0], 'reach': vals[1]}


def _parse_owari(val):
    vals = _parse_str_list(val, type_=float)
    scores = [int(score * 100) for score in vals[::2]]
    return {'scores': scores, 'uma': vals[1::2]}


def _parse_ten(val):
    vals = _parse_str_list(val, type_=int)
    return {'fu': vals[0], 'point': vals[1], 'limit': vals[2]}


def _parse_agari(attrib):
    result = {
        'winner': int(attrib['who']),
        'discarder': int(attrib['fromWho']),
        'hand': _parse_str_list(attrib['hai'], type_=int),
        'machi': _parse_str_list(attrib['machi'], type_=int),
        'dora': _parse_str_list(attrib['doraHai'], type_=int),
        'ura_dora': _parse_str_list(
            attrib.get('doraHaiUra', ''), type_=int),
        'yaku': _nest_list(_parse_str_list(attrib.get('yaku'), type_=int)),
        'yakuman': _parse_str_list(attrib.get('yakuman', ''), type_=int),
        'ten': _parse_ten(attrib['ten']),
        'ba': _parse_ba(attrib['ba']),
        'scores': _nest_list(_parse_score(attrib['sc'])),
    }
    if 'owari' in attrib:
        result['result'] = _parse_owari(attrib['owari'])
    return result


################################################################################
def _parse_dora(attrib):
    return {'hai': int(attrib['hai'])}


###############################################################################
def _parse_ryuukyoku(attrib):
    result = {
        'hands': [
            _parse_str_list(attrib[key], type_=int)
            for key in ['hai0', 'hai1', 'hai2', 'hai3'] if key in attrib
        ],
        'scores': _nest_list(_parse_score(attrib['sc'])),
        'ba': _parse_ba(attrib['ba']),
    }
    if 'type' in attrib:
        result['reason'] = attrib['type']
    if 'owari' in attrib:
        result['result'] = _parse_owari(attrib['owari'])
    return result


###############################################################################
def _parse_bye(attrib):
    return {'player': int(attrib['who'])}


###############################################################################
def _ensure_unicode(data):
    return {
        ensure_unicode(key): ensure_unicode(value)
        for key, value in data.items()
    }


def parse_node(tag, attrib):
    """Parse individual XML node of tenhou mjlog.

    Parameters
    ----------
    tag : str
        Tags such as 'GO', 'DORA', 'AGARI' etc...

    attrib: dict or list
        Attribute of the node

    Returns
    -------
    dict
        JSON object
    """
    attrib = _ensure_unicode(attrib)
    _LG.debug('%s: %s', tag, attrib)
    if tag == 'GO':
        data = _parse_go(attrib)
    elif tag == 'UN':
        if len(attrib) == 1:  # Disconnected player has returned
            data = _parse_resume(attrib)
            tag = 'RESUME'
        else:
            data = _parse_un(attrib)
    elif tag == 'TAIKYOKU':
        data = _parse_taikyoku(attrib)
    elif tag == 'SHUFFLE':
        data = _parse_shuffle(attrib)
    elif tag == 'INIT':
        data = _parse_init(attrib)
    elif tag == 'DORA':
        data = _parse_dora(attrib)
    elif tag[0] in {'T', 'U', 'V', 'W'}:
        data = _parse_draw(tag)
        tag = 'DRAW'
    elif tag[0] in {'D', 'E', 'F', 'G'}:
        data = _parse_discard(tag)
        tag = 'DISCARD'
    elif tag == 'N':
        data = _parse_call(attrib)
        tag = 'CALL'
    elif tag == 'REACH':
        data = _parse_reach(attrib)
    elif tag == 'AGARI':
        data = _parse_agari(attrib)
    elif tag == 'RYUUKYOKU':
        data = _parse_ryuukyoku(attrib)
    elif tag == 'BYE':
        data = _parse_bye(attrib)
    else:
        raise NotImplementedError('{}: {}'.format(tag, attrib))
    _LG.debug('%s: %s', tag, data)
    return {'tag': tag, 'data': data}


###############################################################################
def _validate_structure(parsed, meta, rounds):
    # Verfiy all the items are passed
    if not len(parsed) == len(meta) + sum(len(r) for r in rounds):
        raise AssertionError('Not all the items are structured.')
    # Verfiy all the rounds start with INIT tag
    for round_ in rounds:
        tag = round_[0]['tag']
        if not tag == 'INIT':
            raise AssertionError('Round must start with INIT tag; %s' % tag)


def _structure_parsed_result(parsed):
    """Add structure to parsed log data

    Parameters
    ----------
    parsed : list of dict
        Each item in list corresponds to an XML node in original mjlog file.

    Returns
    -------
    dict
        On top level, 'meta' and 'rounds' key are defined. 'meta' contains
        'SHUFFLE', 'GO', 'UN' and 'TAIKYOKU' keys and its parsed results as
        values. 'rounds' is a list of which items correspond to one round of
        game play.
    """
    round_ = None
    game = {'meta': {}, 'rounds': []}
    for item in parsed:
        tag, data = item['tag'], item['data']
        if tag in ['SHUFFLE', 'GO', 'UN', 'TAIKYOKU']:
            game['meta'][tag] = data
        elif tag == 'INIT':
            if round_ is not None:
                game['rounds'].append(round_)
            round_ = [item]
        else:
            round_.append(item)
    game['rounds'].append(round_)

    _validate_structure(parsed, game['meta'], game['rounds'])
    return game


def parse_mjlog(root_node):
    """Convert mjlog XML node into JSON

    Parameters
    ----------
    root_node (Element)
        Root node of mjlog XML data.

    Returns
    -------
    dict
        Dictionary of of child nodes parsed.
    """
    parsed = [parse_node(node.tag, node.attrib) for node in root_node]
    return _structure_parsed_result(parsed)
