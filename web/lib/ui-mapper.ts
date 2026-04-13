import type { UILeadRecord, SearchProcessStatus } from "@/lib/types";

/** 后端原始 lead（任意 snake_case / 旧字段） */
export function mapBackendLeadToUiRecord(lead: any): UILeadRecord {
  const gradeRaw =
    lead?.final_grade ??
    lead?.customer_grade ??
    lead?.grade ??
    lead?.客户等级 ??
    "D";
  const grade = String(gradeRaw || "D").toUpperCase().slice(0, 1) || "D";

  const score = Number(
    lead?.customer_value_score ?? lead?.total_score ?? lead?.客户符合度分 ?? 0
  );

  const company =
    lead?.company_name ?? lead?.公司名称 ?? lead?.name ?? "";
  const website = lead?.website ?? lead?.官网 ?? "";
  const country = lead?.country ?? lead?.国家 ?? "";
  const industry = lead?.industry ?? lead?.客户类型 ?? "";

  const gradingReason =
    lead?.grading_reason ??
    lead?.分级原因 ??
    "";

  const keySignals =
    Array.isArray(lead?.key_signals)
      ? lead.key_signals.join(" / ")
      : (lead?.key_signals ??
        lead?.关键判断信号 ??
        "");

  const recommended =
    lead?.recommended_contact ??
    lead?.推荐联系人 ??
    formatRecommendedFromParts(lead);

  const contactClues =
    lead?.contact_clues ??
    lead?.联系方式线索 ??
    formatContactCluesFromParts(lead);

  const emailDraft = lead?.email_draft ?? lead?.邮件草稿 ?? "";

  const { status, remark } = deriveStatusAndRemark(lead, grade, score);

  const statusToAction: Record<string, string> = {
    已补全可跟进: "立即跟进",
    "高符合度，需第三次搜索": "第三次搜索",
    "高符合度，需人工搜索": "人工搜索",
    "信息不足，继续背调": "继续背调",
    暂不优先: "暂不优先",
  };

  const nextAction =
    lead?.next_action ??
    lead?.下一步动作 ??
    statusToAction[status] ??
    "待处理";

  const remarkOut =
    lead?.remark ?? lead?.备注 ?? remark ?? "";

  const created =
    lead?.record_created_at ??
    lead?.created_at ??
    lead?.创建时间 ??
    "";

  return {
    公司名称: String(company),
    官网: String(website),
    国家: String(country),
    客户类型: String(industry),
    客户等级: grade,
    客户符合度分: Number.isFinite(score) ? score : 0,
    分级原因: String(gradingReason || inferGradingPlaceholder(lead, grade)),
    关键判断信号: String(
      keySignals || inferKeySignalsPlaceholder(lead, grade, country, industry)
    ),
    推荐联系人: String(recommended),
    联系方式线索: String(contactClues),
    邮件草稿: String(emailDraft),
    搜索处理状态: status as SearchProcessStatus,
    下一步动作: String(nextAction),
    备注: String(remarkOut),
    创建时间: String(created),
  };
}

function formatRecommendedFromParts(lead: any): string {
  const names: string[] = lead?.decision_makers ?? [];
  const titles: string[] = lead?.decision_maker_titles ?? [];
  if (!names.length) return "";
  return names
    .slice(0, 3)
    .map((n, i) => {
      const t = titles[i];
      return t ? `${n} (${t})` : String(n);
    })
    .join(" / ");
}

function formatContactCluesFromParts(lead: any): string {
  const parts: string[] = [];
  const emails: string[] = lead?.emails ?? [];
  const phones: string[] = lead?.contacts ?? [];
  const li: string[] = lead?.linkedin_urls ?? [];
  parts.push(...emails.slice(0, 2).map(String));
  parts.push(...phones.slice(0, 2).map(String));
  for (const u of li.slice(0, 2)) {
    if (String(u).includes("/in/")) parts.push(String(u));
  }
  if (!parts.length && lead?.website) {
    const w = String(lead.website).replace(/\/$/, "");
    parts.push(`${w}/contact`);
  }
  return parts.join(" | ");
}

function deriveStatusAndRemark(
  lead: any,
  grade: string,
  score: number
): { status: string; remark: string } {
  const existing = lead?.search_status ?? lead?.搜索处理状态;
  const existingRemark = lead?.remark ?? lead?.备注;
  if (existing) {
    return { status: String(existing), remark: String(existingRemark ?? "") };
  }

  const hasName = Boolean(
    (lead?.decision_makers?.length ?? 0) > 0 || lead?.decision_maker
  );
  const hasEmail = Boolean((lead?.emails?.length ?? 0) > 0);
  const hasPhone = Boolean((lead?.contacts?.length ?? 0) > 0);
  const linkedins: string[] = lead?.linkedin_urls ?? [];
  const hasIn = linkedins.some((u) => String(u).includes("/in/"));

  if (hasName && (hasEmail || hasPhone || hasIn)) {
    return { status: "已补全可跟进", remark: "" };
  }

  if ((grade === "A" || grade === "B" || score >= 65) && !hasEmail && !hasPhone && !hasIn) {
    return { status: "高符合度，需第三次搜索", remark: "缺联系人方式，仅有官网" };
  }

  if (grade === "A" || grade === "B" || score >= 65) {
    const clues: string[] = [];
    if (linkedins.length && !hasIn) clues.push("仅LinkedIn公司页");
    if (hasName && !hasEmail && !hasPhone) clues.push("有人名无联系方式");
    if (clues.length) {
      return { status: "高符合度，需人工搜索", remark: clues.join("，") };
    }
  }

  if (grade === "C") {
    return { status: "信息不足，继续背调", remark: "需进一步背调" };
  }

  return { status: "暂不优先", remark: "低匹配" };
}

function inferGradingPlaceholder(lead: any, grade: string): string {
  const country = String(lead?.country ?? "");
  const ind = String(lead?.industry ?? "").toLowerCase();
  if (grade === "A" && ["UK", "AU"].includes(country.toUpperCase())) {
    if (ind.includes("retail") || ind.includes("gift")) {
      return "英国礼品买手，主营家居/礼品，匹配我司首选市场";
    }
    return "英澳零售商家，匹配重点市场";
  }
  if (grade === "B") return "市场对/类型对，有合作潜力";
  if (grade === "C") return "边缘匹配，信息待完善";
  if (grade === "D") return "非目标客户，暂不优先";
  return "";
}

function inferKeySignalsPlaceholder(
  lead: any,
  grade: string,
  country: string,
  industry: string
): string {
  const cc = (country || "").toUpperCase();
  const market =
    cc.startsWith("UK") || cc === "GB"
      ? "英国首选市场"
      : cc.startsWith("AU")
        ? "澳洲重点市场"
        : cc.startsWith("US")
          ? "美国培育市场"
          : "非目标市场";
  const ind = (industry || "").toLowerCase();
  let type = "类型：待识别";
  if (ind.includes("retail") || ind.includes("gift")) type = "类型：英澳礼品买手";
  else if (ind.includes("pet")) type = "类型：美国宠物电商";
  else if (ind.includes("wholesale")) type = "类型：大宗批发商";

  const parts = [`市场：${market}`, type];
  if (grade === "D" && ind.includes("wholesale")) {
    parts.push("风险：只比价");
  }
  return parts.join(" / ");
}
