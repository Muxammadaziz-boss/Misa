import asyncio
import edge_tts
import os
import tempfile
import uuid

async def _async_test_voices():
    # 1. Test Madina
    fn_madina = os.path.join(tempfile.gettempdir(), f"test_madina_{uuid.uuid4().hex[:6]}.mp3")
    await edge_tts.Communicate("Salom! Men Madina, Misa AI ning ovozli yordamchisiman.", "uz-UZ-MadinaNeural").save(fn_madina)
    size_madina = os.path.getsize(fn_madina)
    print(f"Madina voice synthesis: SUCCESS ({size_madina} bytes)")
    assert size_madina > 1000

    # 2. Test Sardor
    fn_sardor = os.path.join(tempfile.gettempdir(), f"test_sardor_{uuid.uuid4().hex[:6]}.mp3")
    await edge_tts.Communicate("Assalomu alaykum! Men Sardor, sizning intellektual yordamchingizman.", "uz-UZ-SardorNeural").save(fn_sardor)
    size_sardor = os.path.getsize(fn_sardor)
    print(f"Sardor voice synthesis: SUCCESS ({size_sardor} bytes)")
    assert size_sardor > 1000

    # Cleanup
    if os.path.exists(fn_madina):
        os.remove(fn_madina)
    if os.path.exists(fn_sardor):
        os.remove(fn_sardor)


def test_voices():
    asyncio.run(_async_test_voices())
