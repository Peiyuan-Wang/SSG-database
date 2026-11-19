import fs from 'node:fs/promises';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';
const root = new URL('../../', import.meta.url).pathname;
const path = `${root}outputs/xiao_mapping/SSGclassify_Xiao_67475.xlsx`;
const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(path));
const detail = wb.worksheets.getItem('逐项对应');
const summary = wb.worksheets.getItem('类别汇总');
if (process.argv.includes('--inspect')) {
  console.log((await wb.inspect({kind:'workbook,sheet,table',maxChars:2200,tableMaxRows:2,tableMaxCols:8})).ndjson);
  console.log((await wb.inspect({kind:'region',sheetId:'类别汇总',range:'A21:D39',maxChars:2500,tableMaxRows:19,tableMaxCols:4})).ndjson);
  for (const [sheetName,range,file] of [['逐项对应','A1:H7','detail_before'],['类别汇总','A1:D39','summary_before']]) {
    const blob = await wb.render({sheetName,range,scale:1,format:'png'});
    await fs.writeFile(`${root}tmp/naming_rule/${file}.png`,new Uint8Array(await blob.arrayBuffer()));
  }
  process.exit(0);
}
const input = JSON.parse(await fs.readFile(`${root}tmp/naming_rule/table_rows.json`,'utf8'));
const last = input.rows.length+1;
// Move existing columns with their styles. The original values and formulas
// are independently compared again after export by verify_workbook.py.
detail.getRange(`B1:I${last}`).copyFrom(detail.getRange(`A1:H${last}`),'all');
for (const table of detail.tables.items) table.delete();
detail.getRange('A1').values = [['正式名称（规则 v1.1）']];
detail.getRange('J1:K1').values = [['LaTeX 名称','Hall 编号']];
for (let i=0; i<input.rows.length; i+=4000) {
  const block=input.rows.slice(i,i+4000);
  detail.getRangeByIndexes(i+1,0,block.length,1).values=block.map(r=>[r[0]]);
  detail.getRangeByIndexes(i+1,9,block.length,2).values=block.map(r=>[r[1],r[2]]);
}
detail.getRange(`A1:A${last}`).format.font={name:'Arial',size:11};
detail.getRange(`J1:K${last}`).format.font={name:'Arial',size:11};
detail.getRange(`A1:A${last}`).format.columnWidth=95;
detail.getRange(`J1:J${last}`).format.columnWidth=110;
detail.getRange(`K1:K${last}`).format.columnWidth=14;
for (const [col,width] of [['B',31],['C',14],['D',16],['E',16],['F',24],['G',20],['H',42],['I',20]]) {
  detail.getRange(`${col}1:${col}${last}`).format.columnWidth=width;
}
detail.getRange(`A2:A${last}`).format.wrapText=true;
detail.getRange(`J2:J${last}`).format.wrapText=true;
detail.getRange(`A2:K${last}`).format.verticalAlignment='center';
// Fit formula labels without imposing tall rows on short discrete names.
let start=2, prior=0;
for (let i=0;i<input.rows.length;i++) {
  const r=input.rows[i];
  const height=21*Math.max(1,Math.ceil(r[0].length/85),Math.ceil(r[1].length/100));
  if (i===0) prior=height;
  if (height!==prior) {
    detail.getRange(`A${start}:K${i+1}`).format.rowHeight=prior;
    start=i+2; prior=height;
  }
}
detail.getRange(`A${start}:K${last}`).format.rowHeight=prior;
detail.getRange('A1:K1').format={fill:'#263B63',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',verticalAlignment:'center',rowHeight:27};
detail.getRange(`K2:K${last}`).setNumberFormat('0');
const table=detail.tables.add(`A1:K${last}`,true,'SSGXiaoCorrespondence');
table.showFilterButton=true;
detail.freezePanes.freezeRows(1);
detail.freezePanes.freezeColumns(1);
summary.getRange('A27').values=[['新名称：name_for_label("N143.5.2").text；旧编号仍可查询。']];
summary.getRange('A38').values=[['命名 v1.1：名称包含连续参数域；C 为固定的 HNF 原胞转换矩阵。']];
summary.getRange('A39').values=[['新增名称已做精确回算；Xiao 对应关系及原匹配证明边界保持不变。']];
wb.recalculate();
console.log((await wb.inspect({kind:'region',sheetId:'逐项对应',range:'A1:F4',maxChars:1800,tableMaxRows:4,tableMaxCols:6})).ndjson);
console.log((await wb.inspect({kind:'region',sheetId:'类别汇总',range:'C23:D23',maxChars:500})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:5},maxChars:700})).ndjson);
for (const [sheetName,range,file] of [['逐项对应','A1:F8','detail_after'],['类别汇总','A1:D39','summary_after'],['逐项对应',input.exampleRange,'family_after']]) {
  const blob=await wb.render({sheetName,range,scale:1,format:'png'});
  await fs.writeFile(`${root}tmp/naming_rule/${file}.png`,new Uint8Array(await blob.arrayBuffer()));
}
const output=await SpreadsheetFile.exportXlsx(wb);
await output.save(path);
console.log('EXPORTED',path);
