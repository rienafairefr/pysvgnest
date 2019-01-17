from pytest import raises

from svgnest.cli import parse_args


def test_parse_args():
    parsed = parse_args(['-f', 'FILE',
                         '-f', 'FILE2:2',
                         '-o', 'OUTPUT',
                         '-s', '40x40'])

    assert parsed == ('OUTPUT', {'FILE': 1, 'FILE2': 2}, 40, 40, False)


def test_wrong_args():
    with raises(SystemExit):
        parse_args()


def test_args_no_output():
    with raises(SystemExit):
        parse_args(['-f', 'FILE'])


def test_args_wrong_size():
    with raises(SystemExit):
        parse_args(['-f', 'FILE', '-o', 'OUTPUT', '-s 40:40'])
