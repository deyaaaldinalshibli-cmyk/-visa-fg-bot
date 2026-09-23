import time
import re
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


# ============================================================
# SETTINGS
# ============================================================

URL = "https://appointment.visafg.com/application/"

# ضع بيانات طلبك هنا
DATE_OF_BIRTH = "DD/MM/YYYY"
REFERENCE = "YOUR_BARCODE_OR_REFERENCE"

# ضع بيانات Telegram الخاصة بك هنا
TELEGRAM_BOT_TOKEN = "PUT_YOUR_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID = "PUT_YOUR_CHAT_ID_HERE"

# الفحص كل دقيقة
CHECK_INTERVAL = 60

# أول تشغيل خليه False حتى تشوف المتصفح
HEADLESS = False


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }

    try:
        response = requests.post(
            url,
            data=data,
            timeout=20
        )

        response.raise_for_status()

        print("Telegram message sent successfully.")
        return True

    except Exception as e:
        print(f"Telegram error: {e}")
        return False


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text):
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


# ============================================================
# FIND DATE OF BIRTH FIELD
# ============================================================

def find_dob_input(page):

    try:
        field = page.get_by_label(
            "Date of Birth",
            exact=False
        )

        if field.count() > 0:
            return field.first

    except Exception:
        pass

    inputs = page.locator("input")

    for i in range(inputs.count()):

        field = inputs.nth(i)

        try:
            placeholder = (
                field.get_attribute("placeholder") or ""
            ).lower()

            name = (
                field.get_attribute("name") or ""
            ).lower()

            field_id = (
                field.get_attribute("id") or ""
            ).lower()

            field_type = (
                field.get_attribute("type") or ""
            ).lower()

            info = f"{placeholder} {name} {field_id}"

            if (
                "birth" in info
                or "dob" in info
                or field_type == "date"
            ):
                return field

        except Exception:
            continue

    return None


# ============================================================
# FIND REFERENCE FIELD
# ============================================================

def find_reference_input(page):

    try:
        field = page.get_by_label(
            "Barcode or Reference",
            exact=False
        )

        if field.count() > 0:
            return field.first

    except Exception:
        pass

    inputs = page.locator("input")

    for i in range(inputs.count()):

        field = inputs.nth(i)

        try:
            placeholder = (
                field.get_attribute("placeholder") or ""
            ).lower()

            name = (
                field.get_attribute("name") or ""
            ).lower()

            field_id = (
                field.get_attribute("id") or ""
            ).lower()

            info = f"{placeholder} {name} {field_id}"

            if (
                "barcode" in info
                or "reference" in info
                or "ref" in info
            ):
                return field

        except Exception:
            continue

    return None


# ============================================================
# FIND SEARCH BUTTON
# ============================================================

def click_search(page):

    try:

        button = page.get_by_role(
            "button",
            name="Search",
            exact=False
        )

        if button.count() > 0:
            button.first.click()
            return True

    except Exception:
        pass

    try:

        buttons = page.locator(
            "button, input[type='submit'], input[type='button']"
        )

        for i in range(buttons.count()):

            button = buttons.nth(i)

            try:

                text = (
                    (button.inner_text() or "")
                    + " "
                    + (button.get_attribute("value") or "")
                ).lower()

                if "search" in text:
                    button.click()
                    return True

            except Exception:
                continue

    except Exception:
        pass

    return False


# ============================================================
# CHECK APPLICATION
# ============================================================

def check_application(browser):

    page = browser.new_page()

    try:

        print()
        print("=" * 60)
        print(
            f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Checking application..."
        )
        print("=" * 60)

        # فتح الموقع
        page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        page.wait_for_timeout(2000)

        # ----------------------------------------------------
        # Date of Birth
        # ----------------------------------------------------

        dob_field = find_dob_input(page)

        if dob_field is None:

            print("ERROR: Date of Birth field not found.")

            # حفظ Screenshot للمساعدة في معرفة المشكلة
            page.screenshot(
                path="error_dob.png",
                full_page=True
            )

            return None

        # ----------------------------------------------------
        # Reference
        # ----------------------------------------------------

        reference_field = find_reference_input(page)

        if reference_field is None:

            print("ERROR: Barcode / Reference field not found.")

            page.screenshot(
                path="error_reference.png",
                full_page=True
            )

            return None

        # ----------------------------------------------------
        # Fill fields
        # ----------------------------------------------------

        print("Entering Date of Birth...")

        dob_field.fill(DATE_OF_BIRTH)

        print("Entering Reference...")

        reference_field.fill(REFERENCE)

        page.wait_for_timeout(500)

        # ----------------------------------------------------
        # Search
        # ----------------------------------------------------

        print("Clicking Search...")

        if not click_search(page):

            print("ERROR: Search button not found.")

            page.screenshot(
                path="error_search.png",
                full_page=True
            )

            return None

        print("Search clicked.")

        # انتظار ظهور النتيجة
        page.wait_for_timeout(4000)

        # ----------------------------------------------------
        # Read page
        # ----------------------------------------------------

        body_text = page.locator("body").inner_text()

        print()
        print("WEBSITE RESPONSE:")
        print("-" * 60)
        print(body_text)
        print("-" * 60)

        normalized = normalize_text(body_text)

        # ----------------------------------------------------
        # Check accepted / finalized
        # ----------------------------------------------------

        finalized = (
            "your application has been finalized" in normalized
            and
            "accepted" in normalized
        )

        if finalized:

            print()
            print("############################################")
            print("# APPLICATION FINALIZED AND ACCEPTED      #")
            print("############################################")
            print()

            return {
                "status": "ACCEPTED",
                "text": body_text
            }

        print()
        print("Accepted/finalized message was NOT found.")

        return {
            "status": "NOT_ACCEPTED_YET",
            "text": body_text
        }

    except PlaywrightTimeoutError as e:

        print(f"TIMEOUT ERROR: {e}")

        return None

    except Exception as e:

        print(f"ERROR: {e}")

        return None

    finally:

        page.close()


# ============================================================
# MAIN
# ============================================================

def main():

    # التحقق من الإعدادات

    if DATE_OF_BIRTH == "DD/MM/YYYY":

        print("Please enter your Date of Birth.")
        return

    if REFERENCE == "YOUR_BARCODE_OR_REFERENCE":

        print("Please enter your Reference.")
        return

    if TELEGRAM_BOT_TOKEN == "PUT_YOUR_BOT_TOKEN_HERE":

        print("Please enter your Telegram Bot Token.")
        return

    if TELEGRAM_CHAT_ID == "PUT_YOUR_CHAT_ID_HERE":

        print("Please enter your Telegram Chat ID.")
        return

    print()
    print("=" * 60)
    print("VISA APPLICATION MONITOR")
    print("=" * 60)
    print(f"Checking every {CHECK_INTERVAL} seconds.")
    print()

    telegram_sent = False

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=HEADLESS
        )

        try:

            while True:

                result = check_application(browser)

                if result is None:

                    print("The check failed.")

                elif result["status"] == "ACCEPTED":

                    # إرسال Telegram مرة واحدة فقط
                    if not telegram_sent:

                        message = (
                            "✅ VISA APPLICATION UPDATE\n\n"
                            "Your application has been finalized "
                            "and your file was accepted.\n\n"
                            "You can contact the office for further "
                            "information regarding passport handling, "
                            "delivery, duration of stay, or additional "
                            "documents.\n\n"
                            f"Reference: {REFERENCE}"
                        )

                        if send_telegram(message):

                            telegram_sent = True

                    print("Notification sent.")
                    print("Monitoring stopped.")

                    break

                else:

                    print(
                        f"Next check in "
                        f"{CHECK_INTERVAL} seconds..."
                    )

                time.sleep(CHECK_INTERVAL)

        finally:

            browser.close()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()
