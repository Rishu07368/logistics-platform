"""Optional browser test (needs `pip install playwright && playwright install chromium`).
Start the server first: python run.py   then: python tests/e2e_ui.py [shots_dir]"""
import sys
from playwright.sync_api import sync_playwright

URL, SHOTS = "http://127.0.0.1:5000/", (sys.argv[1] if len(sys.argv) > 1 else None)


def main():
    errors = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" and "422" not in m.text else None)
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(URL); pg.wait_for_selector(".kpi")
        assert "Locations connected" in pg.inner_text("#view")
        shot = lambda n: SHOTS and pg.screenshot(path=f"{SHOTS}/{n}.png")
        shot("overview")
        # optimizer: standard network, Dijkstra route with alternatives
        pg.click("text=Route optimizer"); pg.select_option("#src", "SHA"); pg.select_option("#dst", "JNB")
        pg.click("#calc"); pg.wait_for_selector("text=Optimal cost")
        assert "SHA" in pg.inner_text("#res") and "Relaxations" in pg.inner_text("#res"); shot("optimizer")
        # negative-edge network: Dijkstra blocked, BF works
        pg.select_option("#netSel", label="Negative edges (no cycle)")
        pg.wait_for_function("document.querySelector('#badges').innerText.includes('negative edge')")
        pg.click("text=Route optimizer"); pg.click("#algoSeg button[data-a=dijkstra_heap]"); pg.select_option("#src", "SHA"); pg.select_option("#dst", "JNB")
        pg.click("#calc"); pg.wait_for_selector("text=Dijkstra blocked"); pg.click("#useBf"); pg.wait_for_selector("text=Optimal cost"); shot("negative")
        # negative cycle network
        pg.select_option("#netSel", label="Negative cycle"); pg.wait_for_function("document.querySelector('#badges').innerText.includes('negative cycle')")
        pg.click("text=Route optimizer"); pg.select_option("#src", "SHA"); pg.select_option("#dst", "MUM"); pg.click("#algoSeg button[data-a=auto]"); pg.click("#calc")
        pg.wait_for_selector("text=Cycle:"); shot("cycle")
        # comparison lab on the large network, plus a small benchmark
        pg.select_option("#netSel", label="Large network (300 nodes)"); pg.wait_for_function("document.querySelector('#title').innerText.includes('300')")
        pg.click("text=Comparison lab"); pg.select_option("#src", "N001"); pg.select_option("#dst", "N150"); pg.click("#run"); pg.wait_for_selector("text=Median time")
        pg.fill("#sizes", "20,40,80,160"); pg.click("#bench"); pg.wait_for_selector("text=Measured times", timeout=60000); shot("lab")
        for name in ("Network manager", "Analytics", "Algorithms explained"):
            pg.click(f"nav >> text={name}"); pg.wait_for_timeout(700)
            assert pg.inner_text("#view").strip(), name
            shot(name.split()[0].lower())
        b.close()
    assert not errors, errors
    print("UI test passed")


main()
