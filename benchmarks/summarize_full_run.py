"""Generate human-readable tables from a completed, measured 230-parent run."""
import argparse
import csv
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('directory',type=Path)
    args=parser.parse_args()
    directory=args.directory
    summary=json.loads((directory/'timing_summary.json').read_text())
    assert summary['status']=='complete' and summary['completed_parents']==230
    assert summary['fresh_computation'] and set(summary['requested_parents'])==set(range(1,231))
    assert summary['total_classes']==67475 and len(summary['rows'])==230
    assert all(row['verified'] and row['matches_previous_census'] for row in summary['rows'])
    for row in summary['rows']:
        assert (directory/row['file']).stat().st_size==row['bytes']
    columns=['number','classes','discrete_count','continuous_family_count','charts','relations',
             'enumerate_seconds','export_seconds','read_check_seconds','total_seconds','bytes','file','file_sha256']
    with (directory/'by_parent_timing.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns,extrasaction='ignore')
        writer.writeheader();writer.writerows(summary['rows'])
    with (directory/'by_type.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['type','total','discrete','continuous'])
        for label in sorted(summary['labels'],key=lambda label:('LPN'.index(label[0]),label)):
            n=summary['labels'][label]
            c=summary['continuous_labels'][label]
            writer.writerow([label,n,n-c,c])
    (directory/'SHA256SUMS').write_text(''.join(row['file_sha256']+'  '+row['file']+'\n' for row in summary['rows']))
    def minutes(seconds):
        return '%d 分 %.1f 秒' % (int(seconds//60),seconds%60)
    def local(iso):
        return datetime.fromisoformat(iso).astimezone(timezone(timedelta(hours=8))).isoformat()
    lines=['# 全部 230 个母空间群：完整分类与导出实测','',
           '**本报告记录实际完整运行，不是样本外推。**','',
           '- 开始时间（UTC+8）：'+local(summary['started_at']),
           '- 完成时间（UTC+8）：'+local(summary['ended_at']),
           '- 实际总等待时间：**'+minutes(summary['wall_seconds'])+'**（%.3f 秒）。'%summary['wall_seconds'],
           '- 工作进程：%d；每个母群使用新进程。'%summary['workers'],
           '- 环境：'+summary['machine']+'，Python '+summary['python']+'。',
           '- 完成：230/230；全部使用完整空间自同构去重，开启表示验证。',
           '- 完整目录文件：230 个 JSON，总体积 %.3f GB（十进制）。'%(summary['total_bytes']/1e9),
           '', '## 分类结果','',
           '| 分类 | 数量 |','|---|---:|']
    for d,n in summary['dimensions'].items():lines.append('| '+d+' | '+str(n)+' |')
    lines+=['| 合计 | '+str(summary['total_classes'])+' |','',
            '离散分类：%d；连续参数族：%d。连续族按删除特殊点后的整个域计一族，保存精确参数化和等价关系，不逐点列出无限多个参数值。'%(summary['discrete_count'],summary['continuous_family_count']),
            '', '## 各阶段任务耗时之和','',
            '下面数值是 230 个并行任务各阶段时长的加总，不是实际等待时间，也不是 CPU 时间。实际等待时间以报告开头的墙钟计时为准。','',
            '| 阶段 | 累计任务秒数 |','|---|---:|']
    for k,label in [('enumerate_seconds','加载母群、枚举、三层去重、表示验证'),('export_seconds','整理完整目录、流式写入与释放中间对象'),('read_check_seconds','回读校验、释放对象与文件 SHA-256')]:
        lines.append('| '+label+' | %.3f |'%summary['task_seconds'][k])
    lines+=['', '## 最耗时的母群','',
            '| 母群编号 | 分类数 | 计算/秒 | 导出/秒 | 回读校验/秒 | 总计/秒 | 文件/MB |',
            '|---|---:|---:|---:|---:|---:|---:|']
    for r in sorted(summary['rows'],key=lambda r:r['total_seconds'],reverse=True)[:10]:
        lines.append('| {number} | {classes} | {enumerate_seconds:.2f} | {export_seconds:.2f} | {read_check_seconds:.2f} | {total_seconds:.2f} | {mb:.2f} |'.format(**r,mb=r['bytes']/1e6))
    lines+=['','## 文件和验证范围','',
            '- [每个母群的耗时与文件索引](by_parent_timing.csv)',
            '- [17 类数量](by_type.csv)',
            '- [完整计时数据](timing_summary.json)',
            '- [文件校验值](SHA256SUMS)',
            '- [实际运行日志](run.log)',
            '',
            '`sg001.catalogue.json` 至 `sg230.catalogue.json` 保存各母群的精确旋转、分数平移、乘法表、扩张 cocycle、全部表示图册、分级、连续参数域、轨道代表、空间自同构和等价关系。`class_representatives` 指向每个最终分类在 `charts` 中的代表，`orbits` 保留其图册轨道，`relations` 保留参数作用。',
            '',
            '本次不读取旧的枚举对象，不复用抽样结果；旧统计仅用于完成新计算后的逐母群、逐标签核对。每个文件回读后检查轨道覆盖、代表索引、分类和连续族计数、关系端点、母群指纹及完整正规化子证书，再计算文件 SHA-256。回读结构校验不等同于另一套独立数学分类证明。',
            '',
            '数学核心实现 SHA-256：`'+summary['implementation_sha256']+'`。计时脚本在项目 `benchmarks/full_census_export.py` 中；使用空输出目录执行：',
            '', '```bash','python benchmarks/full_census_export.py --workers 4 --output recomputed_results/new_full_run','```',
            '',
            '与前次抽样相比，本次导出保留相同完整 JSON 内容，采用流式写入；回读前释放中间对象，每个母群完成后回收进程。因此这次时间描述的是该全量执行方式。']
    (directory/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:summary[k] for k in ['status','completed_parents','wall_seconds','total_classes','dimensions','discrete_count','continuous_family_count','total_bytes','task_seconds']},ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
