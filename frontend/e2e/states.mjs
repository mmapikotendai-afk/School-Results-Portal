// Isolated browser fixtures exercise states absent from the local database.
// All API calls are intercepted; no fixture is shipped to the application.
import { chromium, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
const base=process.env.UI_BASE_URL || 'http://127.0.0.1:5173'
const output=resolve('../backend/var/ui-review/states')
await mkdir(output,{recursive:true})
const browser=await chromium.launch({channel:process.env.UI_BROWSER || 'msedge',headless:true,args:['--disable-gpu']})
const findings=[],checks=[]
const longName='Tendai Nyasha Chiedza Mufaro Chikomborero-Makomborero'
const subject={examination_id:7,subject_id:9,subject_name:'Combined Science and Environmental Studies',subject_code:'SCI',examination_name:'End of Term Examination',term_name:'Term 2',status:'PARTIAL',expected_count:3,submitted_count:1,can_upload:true,submission_deadline:'2026-12-01T15:00:00',days_remaining:7,is_past_deadline:false}
const teacher={teacher_name:'Teacher fixture',current_examination:'End of Term Examination',term_name:'Term 2',academic_year_name:'2026',total_subjects:2,submitted_subjects:1,outstanding_subjects:1,overdue_subjects:0,subjects:[subject,{...subject,subject_id:10,subject_name:'Mathematics',subject_code:'MATH',status:'SUBMITTED',submitted_count:3,submitted_at:'2026-10-08T10:00:00'}]}
const entry={examination_id:7,examination_name:'End of Term Examination',academic_year_name:'2026',term_name:'Term 2',is_published:true,published_at:'2026-10-08T10:00:00',subjects_taken:3,average:'74.33',best_subject:'Mathematics',results:[{subject_id:1,subject_name:'Mathematics',subject_code:'MATH',marks:'89',grade:'A',remarks:'Excellent'},{subject_id:2,subject_name:'Combined Science and Environmental Studies',subject_code:'SCI',marks:'76',grade:'B',remarks:'Good progress'},{subject_id:3,subject_name:'English Language',subject_code:'ENG',marks:'58',grade:'C',remarks:'Satisfactory'}]}
const identity={full_name:longName,student_number:'TEST-001',class_name:'Form 4 Cambridge Sciences',level:'O_LEVEL'}
const history={...identity,published_count:1,pending_count:1,entries:[entry,{examination_id:8,examination_name:'Mock Examination',term_name:'Term 3',academic_year_name:'2026',is_published:false,message:'Results are being reviewed.'}]}
const student={...identity,published:[entry],in_progress:[],enrolled_subjects:entry.results.map(r=>r.subject_name)}
const sheet={...subject,can_edit:true,rows:[{student_id:1,student_name:longName,student_number:'TEST-001',marks:76,grade:'B',remarks:'Good progress'},{student_id:2,student_name:'Second student',student_number:'TEST-002',marks:null,grade:null,remarks:null}]}
async function setup(role,viewport={width:390,height:844}) {
 const context=await browser.newContext({viewport,reducedMotion:'reduce'})
 await context.addInitScript(()=>localStorage.setItem('srp.session_expires_at',String(Date.now()+600000)))
 const state={mode:'ready'}
 await context.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname
  let data
  if(path.endsWith('/auth/me'))data={id:1,role:role.toUpperCase(),full_name:longName,email:'fixture@example.test',is_active:true}
  else if(path.endsWith('/teacher/dashboard')) {
   if(state.mode==='loading')await new Promise(resolve=>{state.release=resolve})
   if(state.mode==='error')return route.fulfill({status:503,json:{detail:'The service is temporarily unavailable.'}})
   data=state.mode==='empty'?{...teacher,total_subjects:0,subjects:[]}:teacher
  }
  else if(path.endsWith('/marksheet'))data=sheet
  else if(path.endsWith('/student/history'))data=history
  else if(path.endsWith('/student/results'))data=student
  else if(path.endsWith('/export.pdf'))return route.fulfill({contentType:'application/pdf',headers:{'content-disposition':'attachment; filename="fixture-report.pdf"'},body:'%PDF-1.4\n%%EOF'})
  else return route.fulfill({status:404,json:{detail:'Unconfigured test route'}})
  await route.fulfill({json:data})
 })
 const page=await context.newPage()
 page.on('pageerror',error=>findings.push({issue:error.message}))
 return {context,page,state}
}
async function inspect(page,label,loading=false) {
 if(!loading)await page.waitForLoadState('networkidle')
 await page.evaluate(()=>document.fonts.ready)
 if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))findings.push({label,issue:'page overflow'})
 const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()
 findings.push(...result.violations.map(v=>({label,issue:v.id,nodes:v.nodes.map(n=>n.target)})))
 await page.screenshot({path:resolve(output,label+'.png'),fullPage:true,timeout:60000,animations:'disabled'})
 checks.push(label);console.log('Checked '+label)
}
try {
 const {context,page,state}=await setup('teacher')
 state.mode='loading'
 await page.goto(base+'/teacher/dashboard')
 await page.getByRole('status',{name:'Loading your subjects'}).waitFor()
 await inspect(page,'loading-mobile',true)
 state.mode='ready';state.release()
 await expect(page.getByRole('heading',{name:'Teaching desk',exact:true})).toBeVisible()
 await page.getByRole('button',{name:/Needs marks/}).click()
 await expect(page.locator('.subject-row')).toHaveCount(1)
 await page.getByRole('textbox',{name:'Find a subject'}).fill('no match')
 await expect(page.getByText('No matching subjects')).toBeVisible()
 await page.getByRole('button',{name:'Clear filters'}).click()
 await expect(page.locator('.subject-row')).toHaveCount(2)
 await inspect(page,'teacher-long-subject-mobile')
 await page.getByRole('button',{name:'Upload CSV',exact:true}).first().click()
 await expect(page.getByRole('button',{name:'Validate file'})).toBeDisabled()
 await page.locator('input[type=file]').setInputFiles({name:'test.csv',mimeType:'text/csv',buffer:Buffer.from('student_number,marks\nTEST-001,76')})
 await expect(page.getByRole('button',{name:'Validate file'})).toBeEnabled()
 await inspect(page,'upload-dialog-mobile')
 await page.keyboard.press('Escape')
 await expect(page.getByRole('dialog')).not.toBeVisible()
 state.mode='empty';await page.getByRole('button',{name:'Refresh'}).click()
 await expect(page.getByText('Your subject register is empty')).toBeVisible()
 await inspect(page,'empty-mobile')
 state.mode='error';await page.getByRole('button',{name:'Refresh'}).click()
 await expect(page.getByRole('alert')).toBeVisible()
 await inspect(page,'error-mobile')
 state.mode='ready';await page.getByRole('button',{name:'Try again'}).click()
 await expect(page.locator('.subject-row')).toHaveCount(2)
 await page.getByRole('link',{name:'Enter marks'}).click()
 await expect(page.getByRole('heading',{name:subject.subject_name})).toBeVisible()
 const mark=page.getByRole('spinbutton',{name:'Mark for '+longName})
 await mark.fill('101')
 await expect(page.getByText('Enter 0 to 100').last()).toBeVisible()
 await expect(page.getByRole('button',{name:/Save 1 change/})).toBeDisabled()
 await mark.fill('75')
 await expect(page.getByRole('button',{name:/Save 1 change/})).toBeEnabled()
 await inspect(page,'editable-marks-mobile')
 await page.getByRole('button',{name:'Discard changes'}).click()
 await expect(mark).toHaveValue('76')
 await context.close()
 for(const [size,viewport] of Object.entries({desktop:{width:1440,height:1000},mobile:{width:390,height:844}})) {
  const s=await setup('student',viewport)
  await s.page.goto(base+'/student/dashboard')
  await expect(s.page.getByRole('heading',{name:'Latest published results'})).toBeVisible()
  await inspect(s.page,'published-student-'+size)
  const downloaded=s.page.waitForEvent('download')
  await s.page.getByRole('button',{name:'Download report card',exact:true}).click()
  const download=await downloaded
  if(download.suggestedFilename()!=='fixture-report.pdf')throw new Error('Report download filename mismatch')
  await s.page.goto(base+'/student/results')
  await inspect(s.page,'published-results-'+size)
  // Client-side role guard must return a student to their own workspace.
  await s.page.goto(base+'/admin/dashboard')
  await expect(s.page).toHaveURL(/student/)
  checks.push('student-role-guard-'+size)
  await s.context.close()
 }
} finally {
 await writeFile(resolve(output,'review.json'),JSON.stringify({checks,findings},null,2))
 await browser.close()
}
console.log(JSON.stringify({checks,findings},null,2))
if(findings.length)process.exitCode=1
