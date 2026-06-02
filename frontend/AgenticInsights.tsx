/**
 * S-12 Agentic Insights
 * Deep view into agentic mode sessions — highest cost, highest value.
 * Shows session patterns, tool call distribution, subagent spawning.
 *
 * REAL API CONTRACT:
 *   GET /api/v1/agentic?sprint_id=SPRINT-42&team_id=all
 *   Coding agent: replace MOCK_AGENTIC with api.get('/agentic')
 */

import { useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer,
  Tooltip, Cell, AreaChart, Area,
} from "recharts";
import {
  Cpu, ChevronDown, ArrowUpRight, ArrowDownRight,
  Zap, GitBranch, Clock, DollarSign, FileCode,
  AlertTriangle, ChevronRight,
} from "lucide-react";

const C = {
  bg:"#080808",card:"#101010",surface:"#181818",hover:"#1E1E1E",
  accent:"#00D4FF",accentBg:"rgba(0,212,255,0.08)",
  warm:"#FFB547",warmBg:"rgba(255,181,71,0.08)",
  green:"#00E676",greenBg:"rgba(0,230,118,0.08)",
  red:"#FF4545",redBg:"rgba(255,69,69,0.08)",
  amber:"#FFB800",amberBg:"rgba(255,184,0,0.08)",
  purple:"#A78BFA",purpleBg:"rgba(167,139,250,0.08)",
  text:"#F0F0F0",sub:"#5A5A5A",muted:"#2E2E2E",
  border:"rgba(255,255,255,0.07)",borderHi:"rgba(255,255,255,0.14)",
} as const;
const F={ui:"'Outfit',sans-serif",body:"'DM Sans',sans-serif",mono:"'JetBrains Mono',monospace"};

// GET /api/v1/agentic
const MOCK_AGENTIC = {
  summary:{
    agentic_sessions:89,total_sessions:600,agentic_pct:14.8,
    avg_cost_agentic:1.84,avg_cost_chat:0.28,
    avg_duration_agentic:84,commit_rate:78,
    subagent_spawns:34,
  },
  weekly:[
    {w:"W1",agentic:8,chat:62},{w:"W2",agentic:11,chat:68},
    {w:"W3",agentic:9,chat:59},{w:"W4",agentic:14,chat:74},
    {w:"W5",agentic:16,chat:71},{w:"W6",agentic:19,chat:82},
    {w:"W7",agentic:12,chat:69},{w:"W8",agentic:21,chat:88},
  ],
  tool_calls:[
    {tool:"Write",count:1842,pct:38,color:"#00D4FF"},
    {tool:"Read",count:1241,pct:26,color:"#A78BFA"},
    {tool:"Edit",count:721,pct:15,color:"#FFB547"},
    {tool:"Bash",count:481,pct:10,color:"#FFB800"},
    {tool:"Search",count:312,pct:6,color:"#00E676"},
    {tool:"WebFetch",count:241,pct:5,color:"#FF4545"},
  ],
  developer_breakdown:[
    {name:"Adnan K",tool:"Claude Code",agentic_sessions:18,avg_cost:1.20,avg_dur:74,commit_rate:91,subagents:12,risk_sessions:1},
    {name:"Sara P",tool:"Cursor",agentic_sessions:14,avg_cost:2.10,avg_dur:96,commit_rate:64,subagents:0,risk_sessions:2},
    {name:"Raj K",tool:"Claude Code",agentic_sessions:9,avg_cost:0.94,avg_dur:62,commit_rate:100,subagents:8,risk_sessions:0},
    {name:"Priya M",tool:"Copilot",agentic_sessions:0,avg_cost:0,avg_dur:0,commit_rate:0,subagents:0,risk_sessions:0},
    {name:"Vikram S",tool:"Cursor",agentic_sessions:6,avg_cost:1.64,avg_dur:78,commit_rate:83,subagents:0,risk_sessions:1},
  ],
  top_sessions:[
    {session_id:"s_a1",dev:"Sara P",tool:"Cursor",ticket:"JIRA-151",cost:8.40,dur:180,turns:24,subagents:0,committed:false,risk:"alert",started_at:"28 May 11:00"},
    {session_id:"s_a2",dev:"Adnan K",tool:"Claude Code",ticket:"JIRA-142",cost:3.20,dur:94,turns:12,subagents:4,committed:true,risk:"none",started_at:"28 May 09:28"},
    {session_id:"s_a3",dev:"Raj K",tool:"Claude Code",ticket:"JIRA-155",cost:2.80,dur:82,turns:9,subagents:3,committed:true,risk:"none",started_at:"27 May 14:00"},
    {session_id:"s_a4",dev:"Vikram S",tool:"Cursor",ticket:"JIRA-159",cost:2.40,dur:78,turns:11,subagents:0,committed:true,risk:"watch",started_at:"26 May 16:00"},
    {session_id:"s_a5",dev:"Adnan K",tool:"Claude Code",ticket:"JIRA-142",cost:1.84,dur:68,turns:8,subagents:2,committed:true,risk:"none",started_at:"27 May 10:00"},
  ],
};

function Divider(){return <div style={{height:1,background:C.border}}/>;}
function Tag({children,color,bg}:any){
  return <span style={{padding:"2px 7px",borderRadius:4,background:bg,color,fontFamily:F.mono,fontSize:10,fontWeight:600}}>{children}</span>;
}
const CT=({active,payload,label}:any)=>{
  if(!active||!payload?.length)return null;
  return(
    <div style={{background:C.surface,border:`1px solid ${C.borderHi}`,borderRadius:8,padding:"9px 13px"}}>
      <div style={{fontFamily:F.body,fontSize:10,color:C.sub,marginBottom:5}}>{label}</div>
      {payload.map((p:any,i:number)=>(
        <div key={i} style={{fontFamily:F.mono,fontSize:11,color:p.color||C.accent,fontWeight:600,display:"flex",alignItems:"center",gap:6,marginBottom:2}}>
          <span style={{width:7,height:7,borderRadius:2,background:p.color||C.accent,flexShrink:0}}/>
          {p.name}: {p.value}
        </div>
      ))}
    </div>
  );
};

export default function AgenticInsights(){
  const [hov,setHov]=useState<string|null>(null);
  const s=MOCK_AGENTIC.summary;

  return(
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=DM+Sans:opsz,wght@9..40,400;9..40,500&family=JetBrains+Mono:wght@400;500;600&display=swap');
        *{box-sizing:border-box;margin:0;padding:0}
        ::-webkit-scrollbar{width:4px}::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:2px}
      `}</style>
      <div style={{minHeight:"100vh",background:C.bg,fontFamily:F.body,color:C.text}}>
        {/* Header */}
        <div style={{borderBottom:`1px solid ${C.border}`,padding:"18px 28px 16px",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
          <div>
            <div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginBottom:4}}>Insights · Agentic Insights</div>
            <h1 style={{fontFamily:F.ui,fontSize:22,fontWeight:700,color:C.text,letterSpacing:"-0.02em"}}>Agentic Insights</h1>
            <div style={{fontFamily:F.body,fontSize:12,color:C.sub,marginTop:4}}>Deep analysis of autonomous AI agent sessions — highest cost, highest potential value</div>
          </div>
          <button style={{background:"none",border:`1px solid ${C.border}`,borderRadius:7,padding:"7px 14px",cursor:"pointer",fontFamily:F.body,fontSize:12,color:C.sub,display:"flex",alignItems:"center",gap:6}}>
            Last 30 days <ChevronDown size={12}/>
          </button>
        </div>

        <div style={{padding:"22px 28px",display:"flex",flexDirection:"column",gap:14}}>
          {/* Summary strip */}
          <div style={{display:"flex",background:C.card,border:`1px solid ${C.border}`,borderRadius:10,overflow:"hidden"}}>
            {[
              {label:"Agentic Sessions",value:`${s.agentic_sessions}`,sub:`${s.agentic_pct}% of all sessions`,color:C.accent},
              {label:"Avg Cost (agentic)",value:`$${s.avg_cost_agentic}`,sub:`vs $${s.avg_cost_chat} chat`,color:C.warm},
              {label:"Avg Duration",value:`${s.avg_duration_agentic}min`,sub:"per agentic session",color:C.purple},
              {label:"Commit Rate",value:`${s.commit_rate}%`,sub:"sessions that produced commits",color:C.green},
              {label:"Subagent Spawns",value:`${s.subagent_spawns}`,sub:"Claude Code only",color:C.sub},
            ].map((item,i,arr)=>(
              <div key={i} style={{flex:1,padding:"14px 16px",borderRight:i<arr.length-1?`1px solid ${C.border}`:"none"}}>
                <div style={{fontFamily:F.body,fontSize:9,color:C.sub,textTransform:"uppercase",letterSpacing:"0.07em",marginBottom:5}}>{item.label}</div>
                <div style={{fontFamily:F.mono,fontSize:20,fontWeight:600,color:item.color,lineHeight:1,marginBottom:3}}>{item.value}</div>
                <div style={{fontFamily:F.body,fontSize:10,color:C.sub}}>{item.sub}</div>
              </div>
            ))}
          </div>

          {/* Charts row */}
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:14}}>
            {/* Agentic vs Chat trend */}
            <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:10,overflow:"hidden"}}>
              <div style={{padding:"14px 18px 10px"}}>
                <div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text}}>Agentic vs Chat Sessions</div>
                <div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginTop:2}}>Weekly session count · last 8 weeks</div>
              </div>
              <Divider/>
              <div style={{padding:"12px 8px 8px"}}>
                <ResponsiveContainer width="100%" height={150}>
                  <BarChart data={MOCK_AGENTIC.weekly} margin={{top:4,right:12,bottom:0,left:-12}}>
                    <XAxis dataKey="w" tick={{fontSize:10,fill:C.sub,fontFamily:F.body}} axisLine={false} tickLine={false}/>
                    <YAxis tick={{fontSize:10,fill:C.sub,fontFamily:F.body}} axisLine={false} tickLine={false}/>
                    <Tooltip content={<CT/>}/>
                    <Bar dataKey="chat" name="Chat" fill={C.muted} fillOpacity={0.6} stackId="s" radius={[0,0,0,0]}/>
                    <Bar dataKey="agentic" name="Agentic" fill={C.accent} fillOpacity={0.8} stackId="s" radius={[3,3,0,0]}/>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <Divider/>
              <div style={{padding:"9px 18px",display:"flex",gap:14}}>
                {[{c:C.accent,l:"Agentic"},{c:C.muted,l:"Chat"}].map((l,i)=>(
                  <span key={i} style={{display:"flex",alignItems:"center",gap:6,fontFamily:F.body,fontSize:11,color:C.sub}}>
                    <span style={{width:10,height:10,borderRadius:2,background:l.c}}/>
                    {l.l}
                  </span>
                ))}
              </div>
            </div>

            {/* Tool call distribution */}
            <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:10,overflow:"hidden"}}>
              <div style={{padding:"14px 18px 10px"}}>
                <div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text}}>Tool Call Distribution</div>
                <div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginTop:2}}>What AI agents are doing in agentic sessions</div>
              </div>
              <Divider/>
              <div style={{padding:"10px 0"}}>
                {MOCK_AGENTIC.tool_calls.map((t,i)=>(
                  <div key={i}>
                    <div style={{padding:"8px 18px"}}>
                      <div style={{display:"flex",justifyContent:"space-between",marginBottom:5,alignItems:"center"}}>
                        <span style={{fontFamily:F.mono,fontSize:12,color:C.text}}>{t.tool}</span>
                        <div style={{display:"flex",gap:14,alignItems:"center"}}>
                          <span style={{fontFamily:F.body,fontSize:11,color:C.sub}}>{t.count.toLocaleString()} calls</span>
                          <span style={{fontFamily:F.mono,fontSize:12,fontWeight:600,color:t.color,width:32,textAlign:"right"}}>{t.pct}%</span>
                        </div>
                      </div>
                      <div style={{height:4,background:C.muted,borderRadius:2,overflow:"hidden"}}>
                        <div style={{height:"100%",width:`${t.pct}%`,background:t.color,borderRadius:2,opacity:0.75}}/>
                      </div>
                    </div>
                    {i<MOCK_AGENTIC.tool_calls.length-1&&<Divider/>}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Developer breakdown table */}
          <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:10,overflow:"hidden"}}>
            <div style={{padding:"14px 18px 10px"}}>
              <div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text}}>Developer Agentic Breakdown</div>
              <div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginTop:2}}>Per-developer agentic session stats · Sprint 42</div>
            </div>
            <Divider/>
            <div style={{display:"grid",gridTemplateColumns:"1fr 80px 90px 80px 90px 80px 80px",gap:10,padding:"6px 18px"}}>
              {["Developer","Sessions","Avg Cost","Avg Dur","Commit Rate","Subagents","Risk"].map(h=>(
                <span key={h} style={{fontFamily:F.body,fontSize:10,color:C.sub,textTransform:"uppercase",letterSpacing:"0.07em",fontWeight:600}}>{h}</span>
              ))}
            </div>
            <Divider/>
            {MOCK_AGENTIC.developer_breakdown.map((d,i)=>(
              <div key={i}>
                <div
                  onMouseEnter={()=>setHov(d.name)}
                  onMouseLeave={()=>setHov(null)}
                  style={{display:"grid",gridTemplateColumns:"1fr 80px 90px 80px 90px 80px 80px",gap:10,padding:"11px 18px",alignItems:"center",background:hov===d.name?C.hover:"transparent",cursor:"pointer",transition:"background .1s"}}
                >
                  <div>
                    <div style={{fontFamily:F.body,fontSize:12,color:C.text}}>{d.name}</div>
                    <div style={{fontFamily:F.mono,fontSize:10,color:C.sub}}>{d.tool}</div>
                  </div>
                  <span style={{fontFamily:F.mono,fontSize:12,color:d.agentic_sessions===0?C.sub:C.text}}>{d.agentic_sessions===0?"—":d.agentic_sessions}</span>
                  <span style={{fontFamily:F.mono,fontSize:12,color:d.avg_cost===0?C.sub:C.warm}}>{d.avg_cost===0?"—":`$${d.avg_cost.toFixed(2)}`}</span>
                  <span style={{fontFamily:F.mono,fontSize:12,color:C.sub}}>{d.avg_dur===0?"—":`${d.avg_dur}min`}</span>
                  <div style={{height:4,background:C.muted,borderRadius:2,overflow:"hidden"}}>
                    {d.commit_rate>0&&<div style={{height:"100%",width:`${d.commit_rate}%`,background:d.commit_rate>=80?C.green:d.commit_rate>=60?C.amber:C.red,borderRadius:2}}/>}
                  </div>
                  <span style={{fontFamily:F.mono,fontSize:12,color:d.subagents>0?C.accent:C.sub}}>{d.subagents>0?d.subagents:"—"}</span>
                  {d.risk_sessions>0
                    ?<Tag color={C.red} bg={C.redBg}>{d.risk_sessions} alert{d.risk_sessions>1?"s":""}</Tag>
                    :d.agentic_sessions>0?<Tag color={C.green} bg={C.greenBg}>Clean</Tag>
                    :<span style={{fontFamily:F.body,fontSize:11,color:C.sub}}>—</span>}
                </div>
                {i<MOCK_AGENTIC.developer_breakdown.length-1&&<Divider/>}
              </div>
            ))}
          </div>

          {/* Top costly sessions */}
          <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:10,overflow:"hidden"}}>
            <div style={{padding:"14px 18px 10px"}}>
              <div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text}}>Top Agentic Sessions by Cost</div>
              <div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginTop:2}}>Highest-cost agentic sessions this sprint — click to view session detail</div>
            </div>
            <Divider/>
            <div style={{display:"grid",gridTemplateColumns:"1fr 80px 80px 60px 60px 60px 70px 70px",gap:10,padding:"6px 18px"}}>
              {["Session","Developer","Ticket","Cost","Duration","Turns","Subagents","Risk"].map(h=>(
                <span key={h} style={{fontFamily:F.body,fontSize:10,color:C.sub,textTransform:"uppercase",letterSpacing:"0.07em",fontWeight:600}}>{h}</span>
              ))}
            </div>
            <Divider/>
            {MOCK_AGENTIC.top_sessions.map((s,i)=>{
              const riskColor=s.risk==="alert"?C.red:s.risk==="watch"?C.amber:C.green;
              const riskBg=s.risk==="alert"?C.redBg:s.risk==="watch"?C.amberBg:C.greenBg;
              return(
                <div key={i}>
                  <div
                    onMouseEnter={()=>setHov(s.session_id)}
                    onMouseLeave={()=>setHov(null)}
                    style={{display:"grid",gridTemplateColumns:"1fr 80px 80px 60px 60px 60px 70px 70px",gap:10,padding:"11px 18px",alignItems:"center",background:hov===s.session_id?C.hover:"transparent",cursor:"pointer",transition:"background .1s"}}
                  >
                    <div>
                      <div style={{fontFamily:F.mono,fontSize:10,color:C.sub}}>{s.started_at}</div>
                      <div style={{fontFamily:F.body,fontSize:12,color:C.text}}>{s.tool}</div>
                    </div>
                    <span style={{fontFamily:F.body,fontSize:11,color:C.sub}}>{s.dev}</span>
                    <span style={{fontFamily:F.mono,fontSize:11,color:C.accent}}>{s.ticket}</span>
                    <span style={{fontFamily:F.mono,fontSize:12,fontWeight:600,color:s.cost>5?C.warm:C.text}}>${s.cost.toFixed(2)}</span>
                    <span style={{fontFamily:F.mono,fontSize:11,color:C.sub}}>{s.dur}min</span>
                    <span style={{fontFamily:F.mono,fontSize:11,color:C.sub}}>{s.turns}</span>
                    <span style={{fontFamily:F.mono,fontSize:11,color:s.subagents>0?C.accent:C.sub}}>{s.subagents>0?s.subagents:"—"}</span>
                    <Tag color={riskColor} bg={riskBg}>{s.risk}</Tag>
                  </div>
                  {i<MOCK_AGENTIC.top_sessions.length-1&&<Divider/>}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </>
  );
}
