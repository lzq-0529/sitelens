import { Column, Line } from "@ant-design/plots";
import { ProCard, ProTable } from "@ant-design/pro-components";
import { Alert, Empty, Segmented, Skeleton, Table, Tag } from "antd";
import { useCallback, useEffect, useState } from "react";

export function useLoad(loader, deps) {
  const [state, setState] = useState({ data: null, loading: true, error: "" });
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let alive = true;
    setState((previous) => ({ ...previous, loading: true, error: "" }));
    loader()
      .then((data) => alive && setState({ data, loading: false, error: "" }))
      .catch((exc) => alive && setState((previous) => ({ ...previous, loading: false, error: exc.message })));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);
  const reload = useCallback(() => setTick((value) => value + 1), []);
  return { ...state, reload };
}

export function LoadError({ error }) {
  return error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null;
}

export function DataTable({ columns, search, pagination, ...props }) {
  return (
    <ProTable
      rowKey="id"
      cardBordered
      dateFormatter="string"
      columns={columns.map(({ filter, ...column }) => ({ ...column, search: filter ? (column.search ?? true) : false }))}
      search={
        search === false
          ? false
          : {
              labelWidth: "auto",
              defaultCollapsed: false,
              collapsed: false,
              collapseRender: false,
              span: 4,
              searchGutter: 12,
              ...search,
            }
      }
      pagination={{ defaultPageSize: 20, showSizeChanger: true, pageSizeOptions: [10, 20, 50, 100], showQuickJumper: true, ...pagination }}
      scroll={{ x: "max-content" }}
      options={{ density: true, reload: true, setting: true, fullScreen: true }}
      {...props}
    />
  );
}

export function Kpis({ items, loading, cols = 6 }) {
  const colClass = cols === 4 ? "cols-4" : cols === 5 ? "cols-5" : "";
  return (
    <div className={`sl-kpi-grid ${colClass}`.trim()}>
      {items.map((item) => (
        <div
          key={item.title}
          className={`sl-kpi-card${item.onClick ? " is-clickable" : ""}`}
          style={{ "--kpi-accent": item.color || "#16a34a" }}
          onClick={item.onClick}
        >
          <div className="sl-kpi-head">
            <span className="sl-kpi-title">{item.title}</span>
            {item.badge && <span className="sl-kpi-badge">{item.badge}</span>}
          </div>
          {loading ? <Skeleton.Button active size="small" style={{ width: 96, height: 28 }} /> : <div className="sl-kpi-value">{item.value ?? 0}</div>}
          <div className="sl-kpi-foot">
            <span>{item.hint || "实时统计"}</span>
            {item.sub && <span>{item.sub}</span>}
          </div>
        </div>
      ))}
    </div>
  );
}

export function RankTable({ title, rows, columns, pageSize = 6, height = 276, extra }) {
  const data = (rows || []).map((row, index) => ({ ...row, _key: index }));
  return (
    <ProCard title={title} bordered size="small" extra={extra} className="sl-equal-card">
      <div className="sl-rank-body" style={{ minHeight: height }}>
        <Table
          size="small"
          rowKey="_key"
          dataSource={data}
          columns={columns}
          pagination={data.length > pageSize ? { pageSize, size: "small", showSizeChanger: false } : false}
          scroll={{ y: height - 46, x: "max-content" }}
          locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" /> }}
        />
      </div>
    </ProCard>
  );
}

function NoData({ height, text = "该时间段暂无记录" }) {
  return (
    <div style={{ height, display: "grid", placeItems: "center", background: "#f8fafc", borderRadius: 8 }}>
      <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={text} />
    </div>
  );
}

export function DailyColumn({ data, xField = "day", yField, height = 276, color = "#16a34a", format = (value) => value }) {
  if (!data?.some((row) => row[yField])) return <NoData height={height} />;
  return (
    <Column
      data={data}
      xField={xField}
      yField={yField}
      height={height}
      style={{ fill: color, radiusTopLeft: 4, radiusTopRight: 4 }}
      axis={{ x: { labelAutoHide: true, labelFormatter: (value) => String(value).slice(5) }, y: { labelFormatter: format } }}
      tooltip={{ items: [{ channel: "y", valueFormatter: format }] }}
    />
  );
}

export function DailyLines({ data, height = 300 }) {
  if (!data?.some((row) => row.value)) return <NoData height={height} />;
  return (
    <Line
      data={data}
      xField="day"
      yField="value"
      colorField="series"
      height={height}
      smooth
      point={{ size: 3 }}
      axis={{ x: { labelAutoHide: true, labelFormatter: (value) => String(value).slice(5) } }}
    />
  );
}

export function DaysSwitch({ value, onChange, options = [7, 28, 90] }) {
  return <Segmented value={value} onChange={onChange} options={options.map((days) => ({ value: days, label: `近 ${days} 天` }))} />;
}

export function RegionSwitch({ value, onChange }) {
  return (
    <Segmented
      value={value}
      onChange={onChange}
      options={[
        { value: "all", label: "🌐 国内外汇总" },
        { value: "cn", label: "🇨🇳 国内站" },
        { value: "intl", label: "🌍 海外站" },
      ]}
    />
  );
}

export function RegionTag({ region }) {
  if (region === "intl" || region === "global") return <Tag color="purple">🌍 海外</Tag>;
  if (region === "cn") return <Tag color="blue">🇨🇳 国内</Tag>;
  return <Tag color="cyan">🌐 全区</Tag>;
}

export function SourceTag({ value }) {
  const text = String(value || "").trim() || "直接访问";
  let color = "default";
  if (/知乎|小红书|抖音|头条|B站|微博|Instagram|Pinterest/.test(text)) color = "green";
  else if (/百度|Google|Bing|Yahoo|搜狗/.test(text)) color = "blue";
  else if (/微信|企业微信/.test(text)) color = "cyan";
  return (
    <Tag color={color} style={{ margin: 0, maxWidth: "100%", overflow: "hidden", textOverflow: "ellipsis" }} title={text}>
      {text}
    </Tag>
  );
}
