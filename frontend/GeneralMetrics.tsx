/**
 * S-11 General Metrics
 * DORA metrics + engineering health + AI vs human baseline comparison.
 *
 * REAL API CONTRACT:
 *   GET /api/v1/metrics?sprint_id=SPRINT-42&team_id=all
 */

import { useState } from "react";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, Cell, LineChart, Line, CartesianGrid } from "recharts";
import { TrendingUp, TrendingDown, ChevronDown, Zap } from "lucide-react";

const C={bg:"#080808",card:"#101010",surface:"#181818",hover:"#1E1E1E",accent:"#00D4FF",accentBg:"rgba(0,212,255,0.08)",warm:"#FFB547",green:"#00E676",greenBg:"rgba(0,230,118,0.08)",red:"#FF4545",redBg:"rgba(255,69,69,0.08)",amber:"#FFB800",amberBg:"rgba(255,184,0,0.08)",purple:"#A78BFA",text:"#F0F0F0",sub:"#5A5A5A",muted:"#2E2E2E",border:"rgba(255,255,255,0.07)",borderHi:"rgba(255,255,255,0.14)"} as const;
const F={ui:"'Outfit',sans-serif",body:"'DM Sans',sans-serif",mono:"'JetBrains Mono',monospace"};

const MOCK_METRICS = {
  dora:{deploy_freq:{v:4.2,unit:"per week",trend:+0.8,up:true},lead_time:{v:11.9,unit:"hours P50",trend:-2.1,up:true},change_failure:{v:3.2,unit:"%",trend:-0.8,up:true},mttr:{v:1.4,unit:"hours",trend:-0.3,up:true}},
  ai_context:{ai_prs:8,total_prs:12,ai_pct:67,avg_ai_pr_size:980,avg_human_pr_size:390,ai_review_iterations:1.4,human_review_iterations:2.8,ai_first_pass:72,human_first_pass:41},
  weekly_commits:["W1","W2","W3","W4","W5","W6","W7","W8","W9","W10","W11","W12"].map((w,i)=>({w,ai:Math.floor(12+i*2+Math.random()*4),human:Math.floor(18+Math.random()*6)})),
  pr_merge_time:[
    {range:"<2h",ai:28,human:8},{range:"2-6h",ai:31,human:14},{range:"6-12h",ai:22,human:18},
    {range:"12-24h",ai:12,human:24},{range:">24h",ai:7,human:36},
  ],
  loc_per_dev:[
    {name:"Adnan K",loc:3240,ai_pct:84},
    {name:"Raj K",loc:1840,ai_pct:88},
    {name:"Sara P",loc:2180,ai_pct:71},
    {name:"Priya M",loc:1240,ai_pct:76},
    {name:"Vikram S",loc:890,ai_pct:69},
  ],
};

function Divider(){return <div style={{height:1,background:C.border}}/>;}
function Tag({children,color,bg}:any){
  return <span style={{padding:"2px 7px",borderRadius:4,background:bg,color,fontFamily:F.mono,fontSize:10,fontWeight:600}}>{children}</span>;
}
const CT=({active,payload,label}:any)=>{
  if(!active||!payload?.length)return null;
  return(<div style={{background:C.surface,border:`1px solid ${C.borderHi}`,borderRadius:8,padding:"8px 12px"}}>
    <div style={{fontFamily:F.body,fontSize:10,color:C.sub,marginBottom:5}}>{label}</div>
    {payload.map((p:any,i:number)=>(<div key={i} style={{fontFamily:F.mono,fontSize:11,color:p.color||C.accent,fontWeight:600,marginBottom:2}}>{p.name}: {p.value}</div>))}
  </div>);
};

export default function GeneralMetrics(){
  const m=MOCK_METRICS;
  const dora=[
    {l:"Deploy Frequency",v:`${m.dora.deploy_freq.v}`,unit:m.dora.deploy_freq.unit,trend:`+${m.dora.deploy_freq.trend}`,up:true,color:C.accent},
    {l:"Lead Time",v:`${m.dora.lead_time.v}h`,unit:m.dora.lead_time.unit,trend:`${m.dora.lead_time.trend}h`,up:true,color:C.green},
    {l:"Change Failure Rate",v:`${m.dora.change_failure.v}%`,unit:m.dora.change_failure.unit,trend:`${m.dora.change_failure.trend}%`,up:true,color:C.green},
    {l:"Mean Time to Recovery",v:`${m.dora.mttr.v}h`,unit:m.dora.mttr.unit,trend:`${m.dora.mttr.trend}h`,up:true,color:C.green},
  ];
  return(
    <>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=DM+Sans:opsz,wght@9..40,400;9..40,500&family=JetBrains+Mono:wght@400;500;600&display=swap');*{box-sizing:border-box;margin:0;padding:0}::-webkit-scrollbar{width:4px}::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:2px}`}</style>
      <div style={{minHeight:"100vh",background:C.bg,fontFamily:F.body,color:C.text}}>
        <div style={{borderBottom:`1px solid ${C.border}`,padding:"18px 28px 16px",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
          <div>
            <div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginBottom:4}}>Insights · General Metrics</div>
            <h1 style={{fontFamily:F.ui,fontSize:22,fontWeight:700,color:C.text,letterSpacing:"-0.02em"}}>General Metrics</h1>
            <div style={{fontFamily:F.body,fontSize:12,color:C.sub,marginTop:4}}>Engineering health baseline — DORA metrics and AI vs human delivery comparison</div>
          </div>
          <button style={{background:"none",border:`1px solid ${C.border}`,borderRadius:7,padding:"7px 14px",cursor:"pointer",fontFamily:F.body,fontSize:12,color:C.sub,display:"flex",alignItems:"center",gap:6}}>Last 30 days <ChevronDown size={12}/></button>
        </div>
        <div style={{padding:"22px 28px",display:"flex",flexDirection:"column",gap:14}}>

          {/* Insight callout */}
          <div style={{background:C.accentBg,border:`1px solid rgba(0,212,255,0.15)`,borderRadius:9,padding:"12px 16px",display:"flex",gap:10,alignItems:"center"}}>
            <Zap size={14} color={C.accent}/>
            <span style={{fontFamily:F.body,fontSize:13,color:C.text}}>AI-assisted PRs are merging <span style={{fontFamily:F.mono,color:C.accent,fontWeight:600}}>2.5× faster</span> than human-only PRs this sprint — first-time pass rate improved from 41% to 72%</span>
          </div>

          {/* DORA grid */}
          <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:12}}>
            {dora.map((d,i)=>(
              <div key={i} style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:9,padding:"14px 16px"}}>
                <div style={{fontFamily:F.body,fontSize:10,color:C.sub,textTransform:"uppercase",letterSpacing:"0.06em",marginBottom:8}}>{d.l}</div>
                <div style={{fontFamily:F.mono,fontSize:28,fontWeight:600,color:d.color,lineHeight:1,marginBottom:4}}>{d.v}</div>
                <div style={{fontFamily:F.body,fontSize:10,color:C.sub,marginBottom:6}}>{d.unit}</div>
                <div style={{display:"flex",alignItems:"center",gap:4,fontFamily:F.mono,fontSize:10,color:C.green}}>
                  <TrendingDown size={10} color={C.green}/> {d.trend} vs last period
                </div>
              </div>
            ))}
          </div>

          {/* AI context row */}
          <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:9,padding:"14px 18px"}}>
            <div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text,marginBottom:12}}>AI vs Human — This Sprint</div>
            <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:10}}>
              {[
                {l:"AI PRs",v:`${m.ai_context.ai_prs} of ${m.ai_context.total_prs}`,sub:`${m.ai_context.ai_pct}% of all PRs`,color:C.accent},
                {l:"Avg PR size",v:`${m.ai_context.avg_ai_pr_size}`,sub:`vs ${m.ai_context.avg_human_pr_size} LOC human`,color:C.amber},
                {l:"Review iterations",v:`${m.ai_context.ai_review_iterations}×`,sub:`vs ${m.ai_context.human_review_iterations}× human`,color:C.green},
                {l:"First-time pass",v:`${m.ai_context.ai_first_pass}%`,sub:`vs ${m.ai_context.human_first_pass}% human`,color:C.green},
              ].map((s,i)=>(
                <div key={i} style={{background:C.surface,borderRadius:7,padding:"10px 12px"}}>
                  <div style={{fontFamily:F.body,fontSize:10,color:C.sub,marginBottom:4}}>{s.l}</div>
                  <div style={{fontFamily:F.mono,fontSize:18,fontWeight:600,color:s.color,marginBottom:3}}>{s.v}</div>
                  <div style={{fontFamily:F.body,fontSize:10,color:C.sub}}>{s.sub}</div>
                </div>
              ))}
            </div>
          </div>

          <div style={{display:"grid",gridTemplateColumns:"2fr 1fr",gap:14}}>
            {/* Commit cadence */}
            <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:9,overflow:"hidden"}}>
              <div style={{padding:"12px 16px 9px"}}><div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text}}>Weekly Commit Cadence</div><div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginTop:2}}>AI-touched vs clean commits · last 12 weeks</div></div>
              <Divider/>
              <div style={{padding:"10px 8px 6px"}}>
                <ResponsiveContainer width="100%" height={140}>
                  <BarChart data={m.weekly_commits} margin={{top:4,right:12,bottom:0,left:-12}}>
                    <XAxis dataKey="w" tick={{fontSize:9,fill:C.sub,fontFamily:F.body}} axisLine={false} tickLine={false}/>
                    <YAxis tick={{fontSize:9,fill:C.sub,fontFamily:F.body}} axisLine={false} tickLine={false}/>
                    <Tooltip content={<CT/>}/>
                    <Bar dataKey="human" name="Human" fill={C.muted} fillOpacity={0.8} stackId="c" radius={[0,0,0,0]}/>
                    <Bar dataKey="ai" name="AI-touched" fill={C.accent} fillOpacity={0.7} stackId="c" radius={[3,3,0,0]}/>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <Divider/>
              <div style={{padding:"8px 16px",display:"flex",gap:14}}>
                {[{c:C.accent,l:"AI-touched"},{c:C.muted,l:"Human-only"}].map((l,i)=>(
                  <span key={i} style={{display:"flex",alignItems:"center",gap:5,fontFamily:F.body,fontSize:10,color:C.sub}}><span style={{width:9,height:9,borderRadius:2,background:l.c}}/>{l.l}</span>
                ))}
              </div>
            </div>

            {/* LOC per developer */}
            <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:9,overflow:"hidden"}}>
              <div style={{padding:"12px 16px 9px"}}><div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text}}>LOC per Developer</div><div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginTop:2}}>This sprint · AI acceptance rate</div></div>
              <Divider/>
              <div style={{padding:"8px 0"}}>
                {m.loc_per_dev.map((d,i)=>(
                  <div key={i}>
                    <div style={{padding:"9px 16px"}}>
                      <div style={{display:"flex",justifyContent:"space-between",marginBottom:5}}>
                        <span style={{fontFamily:F.body,fontSize:12,color:C.text}}>{d.name}</span>
                        <div style={{display:"flex",gap:10,alignItems:"center"}}>
                          <span style={{fontFamily:F.mono,fontSize:10,color:C.sub}}>{d.loc.toLocaleString()} LOC</span>
                          <span style={{fontFamily:F.mono,fontSize:11,fontWeight:600,color:d.ai_pct>=80?C.green:d.ai_pct>=70?C.amber:C.red}}>{d.ai_pct}%</span>
                        </div>
                      </div>
                      <div style={{height:4,background:C.muted,borderRadius:2,overflow:"hidden"}}>
                        <div style={{height:"100%",width:`${(d.loc/3240)*100}%`,background:C.accent,borderRadius:2,opacity:0.65}}/>
                      </div>
                    </div>
                    {i<m.loc_per_dev.length-1&&<Divider/>}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* PR merge time */}
          <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:9,overflow:"hidden"}}>
            <div style={{padding:"12px 16px 9px"}}><div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text}}>PR Merge Time Distribution</div><div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginTop:2}}>% of PRs merged within each time window · AI vs human</div></div>
            <Divider/>
            <div style={{padding:"10px 8px 6px"}}>
              <ResponsiveContainer width="100%" height={130}>
                <BarChart data={m.pr_merge_time} margin={{top:4,right:16,bottom:0,left:-12}}>
                  <XAxis dataKey="range" tick={{fontSize:10,fill:C.sub,fontFamily:F.body}} axisLine={false} tickLine={false}/>
                  <YAxis tick={{fontSize:10,fill:C.sub,fontFamily:F.body}} axisLine={false} tickLine={false} tickFormatter={v=>`${v}%`}/>
                  <Tooltip content={<CT/>}/>
                  <Bar dataKey="ai" name="AI-assisted" fill={C.accent} fillOpacity={0.7} radius={[3,3,0,0]}/>
                  <Bar dataKey="human" name="Human-only" fill={C.muted} fillOpacity={0.8} radius={[3,3,0,0]}/>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
