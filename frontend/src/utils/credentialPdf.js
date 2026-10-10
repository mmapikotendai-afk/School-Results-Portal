/** Create a small, offline PDF for one-time student credential slips. */

const pdfText = (value) => String(value ?? '')
  .normalize('NFKD').replace(/[^\x20-\x7e]/g, '')
  .replace(/\\/g, '\\\\').replace(/\(/g, '\\(').replace(/\)/g, '\\)')

function linesFor(slip) {
  const isTeacher = Boolean(slip.teacher_id)
  const personLabel = isTeacher ? 'Teacher' : 'Student'
  const personName = isTeacher ? slip.teacher_name : slip.student_name
  const identifierLabel = isTeacher ? 'Employee number' : 'Student number'
  const identifier = isTeacher ? slip.employee_number : slip.student_number
  return [
    ['BT /F1 20 Tf 54 760 Td (' + pdfText(slip.school_name) + ') Tj ET'],
    ['BT /F1 12 Tf 54 734 Td (' + personLabel + ' portal credentials) Tj ET'],
    ['BT /F1 11 Tf 54 694 Td (' + personLabel + ': ' + pdfText(personName) + ') Tj ET'],
    ['BT /F1 11 Tf 54 670 Td (' + identifierLabel + ': ' + pdfText(identifier) + ') Tj ET'],
    ['BT /F1 11 Tf 54 646 Td (Temporary password: ' + pdfText(slip.temporary_password) + ') Tj ET'],
    ['BT /F1 10 Tf 54 610 Td (Portal: ' + pdfText(slip.portal_url) + ') Tj ET'],
    ['BT /F1 10 Tf 54 578 Td (Sign in with your student number and temporary password.) Tj ET'],
    ['BT /F1 10 Tf 54 560 Td (You must choose a new password immediately. Keep it private.) Tj ET'],
    ['0.75 w 54 710 m 558 710 l S'],
    ['0.75 w 54 625 m 558 625 l S'],
  ].join('\n')
}

export function downloadCredentialPdf(slips) {
  const pages = slips.map(linesFor)
  const pageObjectIds = pages.map((_, index) => 4 + index * 2)
  const contentObjectIds = pages.map((_, index) => 5 + index * 2)
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    `<< /Type /Pages /Kids [${pageObjectIds.map(id => `${id} 0 R`).join(' ')}] /Count ${pages.length} >>`,
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
  ]

  pages.forEach((content, index) => {
    objects.push(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents ${contentObjectIds[index]} 0 R >>`)
    objects.push(`<< /Length ${new TextEncoder().encode(content).length} >>\nstream\n${content}\nendstream`)
  })

  let pdf = '%PDF-1.4\n%\xE2\xE3\xCF\xD3\n'
  const offsets = [0]
  objects.forEach((object, index) => {
    offsets.push(new TextEncoder().encode(pdf).length)
    pdf += `${index + 1} 0 obj\n${object}\nendobj\n`
  })
  const startXref = new TextEncoder().encode(pdf).length
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`
  offsets.slice(1).forEach(offset => { pdf += `${String(offset).padStart(10, '0')} 00000 n \n` })
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${startXref}\n%%EOF`

  const blob = new Blob([pdf], { type: 'application/pdf' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  const isTeacher = Boolean(slips[0]?.teacher_id)
  const identifier = isTeacher ? slips[0]?.employee_number : slips[0]?.student_number
  anchor.download = `${isTeacher ? 'teacher' : 'student'}-credentials-${slips.length === 1 ? identifier : 'batch'}.pdf`
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
