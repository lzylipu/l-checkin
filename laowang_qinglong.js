#!/usr/bin/env node
/**
 * 老王论坛 (laowang.vip) 自动签到 — 青龙面板版
 *
 * 环境变量:
 *   LAOWANG_COOKIE_1  第1个账号cookie (必填)
 *   LAOWANG_COOKIE_2  第2个账号cookie (可选)
 *   ...                最多支持20个账号
 *
 * Cookie格式: 浏览器F12→Application→Cookies→复制全部
 *   示例: "X9wU_2132_saltkey=xxx; X9wU_2132_auth=yyy; ..."
 *
 * 依赖: npm install playwright && npx playwright install chromium
 * 青龙依赖: nodejs, playwright
 */

const { chromium } = require('playwright');

// ==================== 控制变量 ====================
const MAX_RETRIES = 10;       // 滑块验证最大重试次数
const HEADLESS = true;        // 是否无头模式
const TIMEOUT = 60000;        // 页面超时(ms)
const MAX_ACCOUNTS = 20;      // 最大账号数
const RETRY_DELAY = 2000;     // 重试间隔(ms)
// ================================================

const BASE_URL = 'https://laowang.vip';

// 通知函数(兼容青龙通知)
function notify(title, msg) {
  console.log(`📢 ${title}: ${msg}`);
  try { if (typeof sendNotify === 'function') sendNotify(title, msg); } catch(e) {}
}

function parseCookies(cookieStr) {
  return cookieStr.split(';').map(c => c.trim()).filter(c => c).map(pair => {
    const eq = pair.indexOf('=');
    if (eq < 0) return null;
    return { name: pair.substring(0, eq).trim(), value: pair.substring(eq + 1).trim(), domain: 'laowang.vip', path: '/' };
  }).filter(Boolean);
}

async function detectGap(page) {
  return await page.evaluate(() => {
    const c = document.createElement('canvas');
    c.width = 240; c.height = 450;
    const ctx = c.getContext('2d');
    ctx.drawImage(tncode._img, 0, 0);
    const d = ctx.getImageData(0, 0, 240, 450).data;
    let bestX = 0, bestScore = 0, scores = [];
    for (let col = 0; col < 190; col++) {
      let score = 0;
      for (let x = col; x < col + 50; x++) {
        for (let y = 0; y < 150; y++) {
          const i1 = (y * 240 + x) * 4;
          const i2 = ((y + 300) * 240 + x) * 4;
          const dr = d[i1]-d[i2], dg = d[i1+1]-d[i2+1], db = d[i1+2]-d[i2+2];
          score += dr*dr + dg*dg + db*db;
        }
      }
      scores.push(score);
      if (score > bestScore) { bestScore = score; bestX = col; }
    }
    if (bestX > 0 && bestX < 189) {
      const y0 = scores[bestX-1], y1 = scores[bestX], y2 = scores[bestX+1];
      const denom = 2*(2*y1-y0-y2);
      if (denom !== 0) return { gapX: Math.round(bestX + (y0-y2)/denom), bestScore };
    }
    return { gapX: bestX, bestScore };
  });
}

async function dragSlider(page, gapX) {
  const blockRect = await page.evaluate(() => {
    const block = document.querySelector('.slide_block');
    if (!block) return null;
    const r = block.getBoundingClientRect();
    return { left: r.left, top: r.top, width: r.width, height: r.height };
  });
  if (!blockRect) return false;

  const startX = blockRect.left + blockRect.width / 2;
  const startY = blockRect.top + blockRect.height / 2;

  await page.mouse.move(startX, startY);
  await page.mouse.down();
  await page.waitForTimeout(80 + Math.random() * 80);

  // 模拟人类拖动
  const steps = 25 + Math.floor(Math.random() * 10);
  for (let i = 1; i <= steps; i++) {
    const p = i / steps;
    const e = 1 - Math.pow(1 - p, 3);
    const jitter = (i < steps-3) ? (Math.random()-0.5)*3 : (Math.random()-0.5)*1;
    await page.mouse.move(startX + gapX * e, startY + jitter);
    await page.waitForTimeout(i < 5 ? 5+Math.random()*8 : 10+Math.random()*20);
  }

  // 微调回弹
  await page.mouse.move(startX + gapX + Math.random()*3+1, startY);
  await page.waitForTimeout(50 + Math.random()*50);
  await page.mouse.move(startX + gapX, startY);
  await page.waitForTimeout(80 + Math.random()*50);
  await page.mouse.up();
  await page.waitForTimeout(3500);

  const result = await page.evaluate(() => {
    const el = document.getElementById('cliccaptcha-submit-info');
    const ok = document.querySelector('.tncode_msg_ok');
    const err = document.querySelector('.tncode_msg_error');
    return {
      value: el ? el.value : null,
      okMsg: ok ? ok.textContent : null,
      errMsg: err ? err.textContent : null
    };
  });

  if ((result.value && result.value.includes('_ok')) || (result.okMsg && result.okMsg.includes('验证成功'))) {
    return result.value || 'ok';
  }
  return false;
}

async function signIn(cookieStr, accountIdx) {
  const tag = accountIdx > 1 ? `[账号${accountIdx}]` : '';
  console.log(`\n🚀 ${tag} 启动签到...`);

  const browser = await chromium.launch({ headless: HEADLESS });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
  });
  await context.addCookies(parseCookies(cookieStr));
  const page = await context.newPage();
  page.setDefaultTimeout(TIMEOUT);

  try {
    // Step 1: 访问签到页
    console.log(`  ${tag}[1/3] 访问签到页...`);
    await page.goto(`${BASE_URL}/plugin.php?id=k_misign:sign`, { waitUntil: 'networkidle' });

    const uid = await page.evaluate(() => {
      const m = document.documentElement.innerHTML.match(/discuz_uid\s*=\s*['"]?(\d+)/);
      return m ? m[1] : '0';
    });
    if (uid === '0') {
      const msg = `${tag} ❌ 未登录，cookie已失效`;
      console.error(msg);
      notify('老王签到失败', msg);
      return { success: false, msg };
    }
    console.log(`  ${tag} ✓ uid=${uid}`);

    const formhash = await page.evaluate(() => {
      const el = document.querySelector('input[name=formhash]');
      if (el) return el.value;
      const m = document.documentElement.innerHTML.match(/formhash[:=]\s*['"]?([a-f0-9]{8})/);
      return m ? m[1] : null;
    });
    if (!formhash) {
      const msg = `${tag} ❌ 无法获取formhash`;
      console.error(msg);
      notify('老王签到失败', msg);
      return { success: false, msg };
    }
    console.log(`  ${tag} ✓ formhash=${formhash}`);

    // Step 2: 滑块验证
    console.log(`  ${tag}[2/3] 验证滑块...`);
    await page.goto(
      `${BASE_URL}/plugin.php?id=k_misign:sign&operation=qiandao&formhash=${formhash}&format=empty`,
      { waitUntil: 'networkidle' }
    );
    await page.click('.tncode');

    let captchaToken = null;
    for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
      if (attempt > 1) {
        await page.evaluate(() => { if(typeof tncode !== 'undefined') tncode.refresh(); });
        await page.waitForTimeout(RETRY_DELAY);
      }

      try {
        await page.waitForFunction(() =>
          typeof tncode !== 'undefined' && tncode._img &&
          tncode._img.complete && tncode._img.naturalWidth > 0
        , { timeout: 10000 });
      } catch(e) {
        console.log(`  ${tag} 第${attempt}次: 等待加载超时`);
        continue;
      }
      await page.waitForTimeout(2000);

      const gap = await detectGap(page);
      console.log(`  ${tag} 第${attempt}次: gap=${gap.gapX} 置信=${(gap.bestScore/1e6).toFixed(1)}M`);

      const result = await dragSlider(page, gap.gapX);
      if (result) {
        captchaToken = result;
        console.log(`  ${tag} ✓ 滑块验证通过!`);
        break;
      }
    }

    if (!captchaToken) {
      const msg = `${tag} ❌ 滑块验证失败，重试${MAX_RETRIES}次`;
      console.error(msg);
      notify('老王签到失败', msg);
      return { success: false, msg };
    }

    // Step 3: 提交签到
    console.log(`  ${tag}[3/3] 提交签到...`);
    await page.click('#submit-btn');
    await page.waitForTimeout(5000);

    const finalInfo = await page.evaluate(() => {
      const text = document.body.innerText;
      const m = text.match(/连续签到\s*(\d+)\s*天/);
      const lv = text.match(/(\[LV\.\d+\][^\n]*)/);
      return { days: m ? m[1] : null, level: lv ? lv[1] : null, url: location.href };
    });

    if (finalInfo.days || finalInfo.level) {
      const msg = `${tag} 🎉 签到成功! 连续${finalInfo.days||'?'}天 ${finalInfo.level||''}`;
      console.log(msg);
      notify('老王签到', msg);
      return { success: true, msg, days: finalInfo.days, level: finalInfo.level };
    } else {
      const msg = `${tag} ⚠ 提交完成，结果待确认 ${finalInfo.url}`;
      console.log(msg);
      notify('老王签到', msg);
      return { success: true, msg };
    }

  } catch (err) {
    const msg = `${tag} ❌ 执行出错: ${err.message}`;
    console.error(msg);
    notify('老王签到失败', msg);
    return { success: false, msg };
  } finally {
    await browser.close();
  }
}

// ==================== 主入口 ====================
(async () => {
  const accounts = [];
  for (let i = 1; i <= MAX_ACCOUNTS; i++) {
    const val = process.env[`LAOWANG_COOKIE_${i}`];
    if (!val) break;
    accounts.push({ cookie: val, idx: i });
  }

  if (accounts.length === 0) {
    console.error('❌ 未设置任何cookie，请配置环境变量:');
    console.error('   LAOWANG_COOKIE_1=你的cookie');
    console.error('   LAOWANG_COOKIE_2=第二个账号cookie (可选)');
    process.exit(1);
  }

  console.log(`📋 共${accounts.length}个账号`);

  const results = [];
  for (const { cookie, idx } of accounts) {
    const r = await signIn(cookie, idx);
    results.push(r);
    if (idx < accounts.length) await new Promise(r => setTimeout(r, 5000));
  }

  const ok = results.filter(r => r.success).length;
  const fail = results.filter(r => !r.success).length;
  console.log(`\n📊 汇总: 成功${ok} 失败${fail}`);
  if (fail > 0) process.exit(1);
})();
