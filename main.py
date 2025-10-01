import os
import time
from playwright.sync_api import sync_playwright, Cookie

def add_server_time(server_url="https://gpanel.eternalzero.cloud/server/6b6f8709", max_retries=3):
    """
    尝试登录 gpanel.eternalzero.cloud 并点击 "ADD 6H" 按钮。
    优先使用 REMEMBER_WEB_COOKIE 进行会话登录，如果不存在则回退到邮箱密码登录。
    登录失败时会重试最多 max_retries 次。
    """
    # 获取环境变量
    remember_web_cookie = os.environ.get('REMEMBER_WEB_COOKIE')
    login_email = os.environ.get('LOGIN_EMAIL')
    login_password = os.environ.get('LOGIN_PASSWORD')

    # 检查是否提供了任何登录凭据
    if not (remember_web_cookie or (login_email and login_password)):
        print("错误: 缺少登录凭据。请设置 REMEMBER_WEB_COOKIE 或 LOGIN_EMAIL 和 LOGIN_PASSWORD 环境变量。")
        return False

    with sync_playwright() as p:
        # 在 GitHub Actions 中，通常使用 headless 模式
        browser = p.chromium.launch(headless=True)
        
        for attempt in range(1, max_retries + 1):
            print(f"\n=== 尝试第 {attempt}/{max_retries} 次 ===")
            page = browser.new_page()
            
            try:
                login_success = False
                
                # --- 尝试通过 REMEMBER_WEB_COOKIE 会话登录 ---
                if remember_web_cookie:
                    print("尝试使用 REMEMBER_WEB_COOKIE 会话登录...")
                    session_cookie = Cookie(
                        name='remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d',
                        value=remember_web_cookie,
                        domain='.eternalzero.cloud',
                        path='/',
                        expires=time.time() + 3600 * 24 * 365,
                        httpOnly=True,
                        secure=True,
                        sameSite='Lax'
                    )
                    page.context.add_cookies([session_cookie])
                    print(f"已设置 REMEMBER_WEB_COOKIE。正在访问服务器页面: {server_url}")
                    
                    page.goto(server_url, wait_until="networkidle", timeout=60000)

                    # 检查是否成功登录并停留在服务器页面
                    if "login" in page.url or "auth" in page.url:
                        print("使用 REMEMBER_WEB_COOKIE 登录失败或会话无效。将尝试使用邮箱密码登录。")
                        page.context.clear_cookies()
                    else:
                        print("REMEMBER_WEB_COOKIE 登录成功。")
                        if page.url != server_url:
                            print(f"当前URL不是预期服务器页面 ({page.url})，导航到: {server_url}")
                            page.goto(server_url, wait_until="networkidle", timeout=60000)
                        login_success = True

                # --- 如果 REMEMBER_WEB_COOKIE 不可用或失败，则回退到邮箱密码登录 ---
                if not login_success:
                    if not (login_email and login_password):
                        print("错误: REMEMBER_WEB_COOKIE 无效，且未提供 LOGIN_EMAIL 或 LOGIN_PASSWORD。无法登录。")
                        page.close()
                        if attempt < max_retries:
                            print(f"等待 3 秒后重试...")
                            time.sleep(3)
                            continue
                        else:
                            browser.close()
                            return False

                    login_url = "https://gpanel.eternalzero.cloud/auth/login"
                    print(f"正在访问登录页: {login_url}")
                    page.goto(login_url, wait_until="networkidle", timeout=60000)

                    # 登录表单元素选择器
                    email_selector = 'input[name="email"]'
                    password_selector = 'input[name="password"]'
                    login_button_selector = 'button[type="submit"]'

                    print("正在等待登录元素加载...")
                    page.wait_for_selector(email_selector, timeout=30000)
                    page.wait_for_selector(password_selector, timeout=30000)
                    page.wait_for_selector(login_button_selector, timeout=30000)

                    print("正在填充邮箱和密码...")
                    page.fill(email_selector, login_email)
                    page.fill(password_selector, login_password)

                    print("正在点击登录按钮...")
                    page.click(login_button_selector)

                    try:
                        page.wait_for_url(server_url, timeout=60000)
                        print("邮箱密码登录成功，已跳转到服务器页面。")
                        login_success = True
                    except Exception:
                        error_message_selector = '.alert.alert-danger, .error-message, .form-error'
                        error_element = page.query_selector(error_message_selector)
                        if error_element:
                            error_text = error_element.inner_text().strip()
                            print(f"邮箱密码登录失败: {error_text}")
                            page.screenshot(path=f"login_fail_error_message_attempt{attempt}.png")
                        else:
                            print("邮箱密码登录失败: 未能跳转到预期页面或检测到错误信息。")
                            page.screenshot(path=f"login_fail_no_error_attempt{attempt}.png")
                        
                        page.close()
                        if attempt < max_retries:
                            print(f"等待 3 秒后重试...")
                            time.sleep(3)
                            continue
                        else:
                            browser.close()
                            return False

                # --- 如果登录成功，继续执行后续操作 ---
                if login_success:
                    # 确保当前页面是目标服务器页面
                    print(f"当前页面URL: {page.url}")
                    if page.url != server_url:
                        print(f"当前不在目标服务器页面，导航到: {server_url}")
                        page.goto(server_url, wait_until="networkidle", timeout=60000)
                        if page.url != server_url and ("login" in page.url or "auth" in page.url):
                            print("导航到服务器页面失败，可能需要重新登录或会话已过期。")
                            page.screenshot(path=f"server_page_nav_fail_attempt{attempt}.png")
                            page.close()
                            if attempt < max_retries:
                                print(f"等待 3 秒后重试...")
                                time.sleep(3)
                                continue
                            else:
                                browser.close()
                                return False

                    # --- 查找 "ADD 6H" 按钮并检查是否可点击 ---
                    add_button_selector = 'button:has-text("ADD 6H")'
                    print(f"正在查找 '{add_button_selector}' 按钮")

                    try:
                        page.wait_for_selector(add_button_selector, state='visible', timeout=30000)
                        button = page.query_selector(add_button_selector)
                        
                        if button:
                            # 检查按钮是否被禁用
                            is_disabled = button.is_disabled()
                            has_disabled_attr = button.get_attribute('disabled') is not None
                            
                            if is_disabled or has_disabled_attr:
                                print("'ADD 6H' 按钮当前不可点击（已禁用），无需续期。")
                                page.screenshot(path="button_disabled.png")
                                page.close()
                                browser.close()
                                return True
                            else:
                                print("'ADD 6H' 按钮可点击，正在执行点击操作...")
                                page.click(add_button_selector)
                                print("成功点击 'ADD 6H' 按钮。")
                                time.sleep(5)
                                print("等待 5 秒后继续。")
                                page.screenshot(path="button_clicked.png")
                                page.close()
                                browser.close()
                                return True
                        else:
                            print("未找到 'ADD 6H' 按钮元素，可能无需续期。")
                            page.screenshot(path="button_not_found.png")
                            page.close()
                            browser.close()
                            return True
                            
                    except Exception as e:
                        print(f"查找或处理 'ADD 6H' 按钮时发生错误: {e}")
                        print("按钮不可用，可能无需续期。")
                        page.screenshot(path="extend_button_error.png")
                        page.close()
                        browser.close()
                        return True

            except Exception as e:
                print(f"执行过程中发生未知错误: {e}")
                page.screenshot(path=f"general_error_attempt{attempt}.png")
                page.close()
                if attempt < max_retries:
                    print(f"等待 3 秒后重试...")
                    time.sleep(3)
                    continue
                else:
                    browser.close()
                    return False
        
        browser.close()
        return False

if __name__ == "__main__":
    print("开始执行添加服务器时间任务...")
    success = add_server_time()
    if success:
        print("任务执行成功。")
        exit(0)
    else:
        print("任务执行失败。")
        exit(1)
