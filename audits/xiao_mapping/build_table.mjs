import fs from 'node:fs/promises';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const root = new URL('../../', import.meta.url).pathname;
const input = JSON.parse(await fs.readFile(`${root}audits/xiao_mapping/table_data.json`, 'utf8'));
const outputDir = `${root}outputs/xiao_mapping`;
await fs.mkdir(outputDir, { recursive: true });
const wb = Workbook.create();
const summary = wb.worksheets.add('类别汇总');
const detail = wb.worksheets.add('逐项对应');
summary.showGridLines = false;
detail.showGridLines = false;
summary.tabColor = '#263B63';
summary.getRange('A2').values = [['SSGclassify 与 Xiao 完整编号对应']];
summary.getRange('A2').format.font = { name: 'Arial', size: 15, bold: true };
summary.getRange('A4:D4').values = [['我们的类型', 'Xiao 类型: 分类数', '分类总数', '连续族数']];
summary.getRange('A5:D21').values = input.summary;
summary.getRange('A23').values = [['合计']];
summary.getRange('C23:D23').formulas = [['=SUM(C5:C21)', '=SUM(D5:D21)']];
summary.getRange('A25').values = [['覆盖 230 个母空间群；L 1421，P 9542，N 56512。']];
summary.getRange('A27').values = [['编号查询：to_xiao_label("SG143/N.1.2/0002") → N143.5.2']];
summary.getRange('A29').values = [['验证：全部 67475 个条目唯一匹配，8520 个连续族通过第二组参数检查。']];
summary.getRange('A30').values = [['边界：含数值自旋基底求解；两组参数检查不是全参数符号证明。']];
summary.getRange('A32').values = [['我们的序号固定于 full_export_230_20261029；完整用法见项目 docs/XIAO_LABEL_MAPPING_ZH.md。']];
summary.getRange('A34').values = [['论文来源：Xiao 等，Physical Review X 14, 031037；ISO-IR 表示数据库。']];
summary.getRange('A35').values = [[input.metadata.supplement_url]];
summary.getRange('A36').values = [['https://iso.byu.edu/irtables.php']];
summary.getRange('A38').values = [['每行是一种分类；“连续参数个数”属于该行所保存的表示图表。']];
summary.getRange('A39').values = [['ISO-IR 表示组成包含论文简写可能省略的平凡表示。']];
summary.getRange('A4:D39').format.font = { name: 'Arial', size: 11 };
summary.getRange('A4:D23').format.rowHeight = 22;
summary.getRange('A4:D4').format = {fill:'#263B63',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',verticalAlignment:'center'};
summary.getRange('A23:D23').format.font.bold = true;
summary.getRange('C5:D23').setNumberFormat('#,##0');
for (const [col,width] of [['A',22],['B',72],['C',16],['D',16]]) {
  summary.getRange(`${col}1:${col}39`).format.columnWidth = width;
}
summary.getRange('A25:D39').format.rowHeight = 23;

const last = input.rows.length + 1;
detail.getRange('A1:H1').values = [input.headers];
for (let i = 0; i < input.rows.length; i += 5000) {
  const block = input.rows.slice(i, i+5000);
  detail.getRangeByIndexes(i+1, 0, block.length, 8).values = block;
}
console.log('Rows written:', input.rows.length);
detail.getRange(`A1:H${last}`).format.font = {name:'Arial',size:11};
detail.getRange(`A1:H${last}`).format.rowHeight = 21;
detail.getRange(`A1:H${last}`).format.verticalAlignment = 'center';
detail.getRange('A1:H1').format = {fill:'#263B63',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',verticalAlignment:'center',rowHeight:27};
for (const [col,width] of [['A',31],['B',14],['C',16],['D',16],['E',24],['F',20],['G',42],['H',20]]) {
  detail.getRange(`${col}1:${col}${last}`).format.columnWidth = width;
}
for (const col of ['B','D','F','H']) detail.getRange(`${col}2:${col}${last}`).setNumberFormat('0');
const table = detail.tables.add(`A1:H${last}`,true,'SSGXiaoCorrespondence');
table.showFilterButton = true;
detail.freezePanes.freezeRows(1);
detail.freezePanes.freezeColumns(1);
wb.recalculate();
console.log((await wb.inspect({kind:'region',sheetId:'类别汇总',range:'A21:D23',maxChars:1200,tableMaxRows:3,tableMaxCols:4})).ndjson);
console.log((await wb.inspect({kind:'region',sheetId:'逐项对应',range:'A1:H4',maxChars:1500,tableMaxRows:4,tableMaxCols:8})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:10},maxChars:1000})).ndjson);
for (const [name,range,file] of [['类别汇总','A1:D39','summary'],['逐项对应','A1:H13','detail']]) {
  const blob = await wb.render({sheetName:name,range,scale:1.4,format:'png'});
  await fs.writeFile(`${root}tmp/xiao_${file}.png`,new Uint8Array(await blob.arrayBuffer()));
}
const output = await SpreadsheetFile.exportXlsx(wb);
await output.save(`${outputDir}/SSGclassify_Xiao_67475.xlsx`);
console.log('EXPORTED',`${outputDir}/SSGclassify_Xiao_67475.xlsx`);
