import pytest

from electrumx.lib.script import OpCodes, is_unspendable_legacy


@pytest.mark.parametrize("script", (
    bytes([OpCodes.OP_RETURN]),
    bytes([OpCodes.OP_RETURN]) + bytes([2, 28, 50]),
    bytes([OpCodes.OP_0, OpCodes.OP_RETURN]),
    bytes([OpCodes.OP_0, OpCodes.OP_RETURN]) + bytes([2, 28, 50]),
))
def test_op_return(script):
    assert is_unspendable_legacy(script)


@pytest.mark.parametrize("script", (
    bytes([]),
    bytes([OpCodes.OP_1, OpCodes.OP_RETURN]) + bytes([2, 28, 50]),
    bytes([OpCodes.OP_0]),
    bytes([OpCodes.OP_0, OpCodes.OP_1]),
    bytes([OpCodes.OP_HASH160]),
))
def test_not_op_return(script):
    assert not is_unspendable_legacy(script)
