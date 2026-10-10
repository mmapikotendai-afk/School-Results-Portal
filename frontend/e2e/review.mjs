/**
 * Read-only local browser review. Requires the running frontend/backend and
 * the local backend virtualenv/database. Tokens remain in memory and expire
 * in ten minutes; no passwords, account changes or database writes are used.
 * Screenshots may contain local school records: artifacts stay in ignored var/.
 */
import { chromium } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { execFileSync } from 'node:child_process'
import { mkdir, writeFile, readFile } from 'node:fs/promises'
import { resolve } from 'node:path'

const base = process.env.UI_BASE_URL || 'http://127.0.0.1:5173'
const output = resolve('../backend/var/ui-review')
await mkdir(output, {recursive:true})
const python = resolve('../backend/.venv/Scripts/python.exe')
const sessions = JSON.parse(execFileSync(python, ['-c', `
import json
from datetime import timedelta
from sqlalchemy import select
from app import models
from app.database import SessionLocal
from app.models.user import User
from app.models.enums import UserRole
from app.auth.jwt import create_access_token
from app.config import settings
sessions={}
with SessionLocal() as db:
 for role in UserRole:
  user=db.scalar(select(User).where(User.role==role,User.is_active==True).order_by(User.id))
  if user:
   token,_,expiry=create_access_token(user.id,role.value,user.token_version,expires_delta=timedelta(minutes=10))
   sessions[role.value.lower()]={'token':token,'cookie':settings.SESSION_COOKIE_NAME,'expiry':int(expiry.timestamp()*1000),'mustChange':user.must_change_password}
print(json.dumps(sessions))
`], {cwd:resolve('../backend'),env:{...process.env,DEBUG:'false'},encoding:'utf8'}))
const browser = await chromium.launch({channel:process.env.UI_BROWSER || 'msedge',headless:true,args:['--disable-gpu']})
const previous = process.env.UI_REVIEW_RESUME ? JSON.parse(await readFile(resolve(output,'review.json'),'utf8')) : {checks:[],findings:[]}
const findings=previous.findings
const checks=previous.checks
const sizes={desktop:{width:1440,height:1000},laptop:{width:1280,height:800},tablet:{width:820,height:1180},mobile:{width:390,height:844}}
async function contextFor(role, size) {
 const context=await browser.newContext({viewport:size,reducedMotion:'reduce'})
 if (role) {
  const session=sessions[role]
  if (!session) throw new Error('No active local account for '+role)
  await context.addCookies([{name:session.cookie,value:session.token,url:base,httpOnly:true,sameSite:'Lax'}])
  await context.addInitScript(expiry => localStorage.setItem('srp.session_expires_at',String(expiry)),session.expiry)
 }
 // This review must never modify school data.
 await context.route('**/api/**',async route => {
  if (!['GET','HEAD','OPTIONS'].includes(route.request().method())) return route.abort('blockedbyclient')
  return route.continue()
 })
 return context
}
async function settle(page) {
 await page.waitForLoadState('networkidle')
 await page.evaluate(() => document.fonts.ready)
}
async function inspect(page,label,{capture=true,axe=true}={}) {
 if(checks.includes(label)) return
 await settle(page)
 const overflow=await page.evaluate(() => document.documentElement.scrollWidth > innerWidth+1)
 if(overflow) findings.push({label,issue:'page overflow'})
 if(axe) {
  const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()
  findings.push(...result.violations.map(v=>({label,issue:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})))
 }
 if(capture) await page.screenshot({path:resolve(output,label+'.png'),fullPage:true,timeout:60000,animations:'disabled'})
 checks.push(label)
 console.log('Reviewed '+label)
}
try {
 for(const [size,viewport] of Object.entries(sizes)) {
  for(const role of ['admin','teacher','student']) {
   const context=await contextFor(role,viewport)
   const page=await context.newPage()
   page.on('pageerror',error=>findings.push({label:role+'-'+size,issue:error.message}))
   page.on('console',msg=>{if(msg.type()==='error' && !msg.text().includes('Failed to load resource'))findings.push({label:role+'-'+size,issue:msg.text()})})
   await page.goto(base+'/'+role+'/dashboard')
   await page.getByRole('heading',{level:1}).waitFor()
   if(sessions[role]?.mustChange) {
    await inspect(page,role+'-first-password-'+size)
    await context.close()
    continue
   }
   await inspect(page,role+'-'+size)
   if(role==='teacher') {
    const upload=page.getByRole('button',{name:'Upload CSV',exact:true}).first()
    if(await upload.isVisible()) {
     await upload.click();await inspect(page,'teacher-import-'+size)
     await page.keyboard.press('Escape')
    }
    const sheetLink=page.getByRole('link',{name:/^(Enter marks|Manage marks|View results)$/}).first()
    if(await sheetLink.isVisible()) {
     await sheetLink.click();await inspect(page,'teacher-marks-'+size)
    }
   }
   if(role==='admin') {
    if(size==='desktop') {
     await page.getByRole('button',{name:'Collapse navigation'}).click()
     await inspect(page,'admin-collapsed')
     await page.getByRole('button',{name:'Expand navigation'}).click()
    }
    if(size==='mobile') {
     await page.getByRole('button',{name:'Open navigation menu'}).click()
     await inspect(page,'mobile-navigation')
     await page.keyboard.press('Escape')
     if(await page.getByRole('dialog').isVisible())findings.push({issue:'Escape did not close mobile drawer'})
     if(!await page.getByRole('button',{name:'Open navigation menu'}).evaluate(el=>el===document.activeElement))findings.push({issue:'Drawer did not restore trigger focus'})
    }
    await page.goto(base+'/admin/students')
    await inspect(page,'students-'+size)
    await page.getByRole('button',{name:'Add student',exact:true}).click()
    await inspect(page,'student-form-'+size)
    await page.keyboard.press('Escape')
   }
   await context.close()
  }
  if(size==='desktop'||size==='mobile') {
   const context=await contextFor(null,viewport)
   const page=await context.newPage()
   await page.goto(base+'/login');await inspect(page,'login-'+size)
   await page.goto(base+'/');await inspect(page,'landing-'+size)
   await context.close()
  }
 }
 const routes={
  admin:['teachers','reset-requests','subjects','classes','academic-years','terms','examinations','submissions','results','reports','settings','students/import'],
  teacher:['results','upload','submissions','downloads','settings'],
  student:['results','previous','downloads','settings']
 }
 for(const [role,paths] of Object.entries(routes)) {
  if(sessions[role]?.mustChange) continue
  const context=await contextFor(role,sizes.desktop)
  const page=await context.newPage()
  page.on('pageerror',error=>findings.push({label:role+'-pages',issue:error.message}))
  for(const path of paths) {
   await page.goto(base+'/'+role+'/'+path)
   await inspect(page,role+'-'+path.replace('/','-'),{capture:false})
  }
  await context.close()
 }
} finally {
 await writeFile(resolve(output,'review.json'),JSON.stringify({checks,findings},null,2))
 await browser.close()
}
console.log(JSON.stringify({checks:checks.length,findings},null,2))
if(findings.length)process.exitCode=1
