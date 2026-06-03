/**
 * S-13 Sprint Detail Drill-Down
 * Everything about one sprint — cost, tickets, quality.
 * Reached from: ROI view → click sprint row.
 *
 * REAL API CONTRACT:
 *   GET /api/v1/sprints/:sprintId
 *   GET /api/v1/sprints/:sprintId/tickets
 */

import { useState } from "react";
import { ArrowLeft, ChevronDown, BarChart2, TrendingUp, DollarSign, GitCommit, Download } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, Cell } from "recharts";

const C={bg:"#080808",card:"#101010",surface:"#181818",hover:"#1E1E1E",accent:"#00D4FF",accentBg:"rgba(0,212,255,0.08)",warm:"#FFB547",warmBg:"rgba(255,181,71,0.08)",green:"#00E676",greenBg:"rgba(0,230,118,0.08)",red:"#FF4545",redBg:"rgba(255,69,69,0.08)",amber:"#FFB800",amberBg:"rgba(255,184,0,0.08)",purple:"#A78BFA",text:"#F0F0F0",sub:"#5A5A5A",muted:"#2E2E2E",border:"rgba(255,255,255,0.07)",borderHi:"rgba(255,255,255,0.14)"} as const;
const F={ui:"'Outfit',sans-serif",body:"'DM Sans',sans-serif",mono:"'JetBrains Mono',monospace"};

const MOCK_SPRINT = {
  sprint:{id:"SPRINT-42",name:"Sprint 42",status:"active",started_at:"2026-05-19",ends_at:"2026-06-02",tickets:15,developers:7,sessions:89},
  summary:{total_ai_spend:312,tickets_completed:8,cost_per_ticket:17.50,roi_multiplier:3.2,vs_previous:{spend:+32,tickets:+1,cost_per_ticket:-2.10}},
  daily_spend:[
    {d:"Mon 19",v:28},{d:"Tue 20",v:42},{d:"Wed 21",v:38},{d:"Thu 22",v:51},
    {d:"Fri 23",v:44},{d:"Sat 24",v:8},{d:"Mon 26",v:35},{d:"Tue 27",v:48},
    {d:"Wed 28",v:18},{d:"Thu 29",v:0},{d:"Fri 30",v:0},
  ],
  dev_spend:[
    {name:"Adnan K",spend:142,pct:45.5},{name:"Sara P",spend:98,pct:31.4},
    {name:"Raj K",spend:67,pct:21.5},{name:"Priya M",spend:53,pct:17.0},
    {name:"Vikram S",spend:38,pct:12.2},{name:"Meera T",spend:12,pct:3.8},
    {name:"Kiran R",spend:0,pct:0},
  ],
  tickets:[
    {id:"JIRA-142",title:"Stripe payment gateway",dev:"Adnan K",cost:4.20,sessions:3,ai_pct:82,status:"done",roi:3.2,risk:"none"},
    {id:"JIRA-151",title:"Data pipeline refactor",dev:"Sara P",cost:8.40,sessions:7,ai_pct:71,status:"active",roi:null,risk:"alert"},
    {id:"JIRA-155",title:"Auth SSO integration",dev:"Raj K",cost:3.10,sessions:2,ai_pct:88,status:"done",roi:4.1,risk:"none"},
    {id:"JIRA-159",title:"Search & filter API",dev:"Priya M",cost:6.80,sessions:5,ai_pct:76,status:"active",roi:null,risk:"none"},
    {id:"JIRA-163",title:"Mobile push notifications",dev:"Adnan K",cost:2.90,sessions:2,ai_pct:69,status:"review",roi:null,risk:"none"},
    {id:"JIRA-167",title:"Analytics event tracking",dev:"Sara P",cost:11.20,sessions:9,ai_pct:43,status:"active",roi:null,risk:"alert"},
    {id:"JIRA-171",title:"User profile settings",dev:"Raj K",cost:1.80,sessions:1,ai_pct:91,status:"done",roi:5.4,risk:"none"},
    {id:"JIRA-175",title:"Dashboard performance fix",dev:"Priya M",cost:0.90,sessions:1,ai_pct:74,status:"done",roi:2.8,risk:"none"},
  ],
};

function Divider(){return <div style={{height:1,background:C.border}}/>;}
function Tag({children,color,bg}:any){
  return <span style={{padding:"2px 7px",borderRadius:4,background:bg,color,fontFamily:F.mono,fontSize:10,fontWeight:600}}>{children}</span>;
}
const CT=({active,payload,label}:any)=>{
  if(!active||!payload?.length)return null;
  return(<div style={{background:C.surface,border:`1px solid ${C.borderHi}`,borderRadius:8,padding:"8px 12px"}}>
    <div style={{fontFamily:F.body,fontSize:10,color:C.sub,marginBottom:4}}>{label}</div>
    <div style={{fontFamily:F.mono,fontSize:12,color:C.warm,fontWeight:600}}>${payload[0].value}</div>
  </div>);
};

export default function SprintDetail(){
  const [hov,setHov]=useState<string|null>(null);
  const [compare,setCompare]=useState(false);
  const sp=MOCK_SPRINT;

  return(
    <>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=DM+Sans:opsz,wght@9..40,400;9..40,500&family=JetBrains+Mono:wght@400;500;600&display=swap');*{box-sizing:border-box;margin:0;padding:0}::-webkit-scrollbar{width:4px}::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:2px}`}</style>
      <div style={{minHeight:"100vh",background:C.bg,fontFamily:F.body,color:C.text}}>
        {/* Breadcrumb */}
        <div style={{borderBottom:`1px solid ${C.border}`,padding:"12px 28px",display:"flex",alignItems:"center",gap:10}}>
          <button style={{background:"none",border:"none",cursor:"pointer",color:C.sub,display:"flex",alignItems:"center",gap:5,fontFamily:F.body,fontSize:12}}>
            <ArrowLeft size={14}/> ROI View
          </button>
          <span style={{color:C.muted}}>·</span>
          <span style={{fontFamily:F.body,fontSize:12,color:C.sub}}>Sprint 42</span>
        </div>
        {/* Header */}
        <div style={{borderBottom:`1px solid ${C.border}`,padding:"16px 28px",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
          <div>
            <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:4}}>
              <h1 style={{fontFamily:F.ui,fontSize:22,fontWeight:700,color:C.text,letterSpacing:"-0.02em"}}>Sprint 42</h1>
              <Tag color={C.green} bg={C.greenBg}>Active</Tag>
            </div>
            <div style={{fontFamily:F.body,fontSize:12,color:C.sub}}>
              {sp.sprint.started_at} → {sp.sprint.ends_at} · {sp.sprint.tickets} tickets · {sp.sprint.developers} developers · {sp.sprint.sessions} AI sessions
            </div>
          </div>
          <div style={{display:"flex",gap:8}}>
            <button onClick={()=>setCompare(p=>!p)} style={{background:compare?C.accentBg:"none",border:`1px solid ${compare?"rgba(0,212,255,0.3)":C.border}`,borderRadius:7,padding:"7px 14px",cursor:"pointer",fontFamily:F.body,fontSize:12,color:compare?C.accent:C.sub}}>
              Compare to S41
            </button>
            <button style={{background:"none",border:`1px solid ${C.border}`,borderRadius:7,padding:"7px 14px",cursor:"pointer",fontFamily:F.body,fontSize:12,color:C.sub,display:"flex",alignItems:"center",gap:5}}>
              <Download size={12}/> Export
            </button>
          </div>
        </div>

        <div style={{padding:"22px 28px",display:"flex",flexDirection:"column",gap:14}}>
          {/* Summary cards */}
          <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:12}}>
            {[
              {l:"Total AI Spend",v:`$${sp.summary.total_ai_spend}`,delta:`+$${sp.summary.vs_previous.spend} vs S41`,up:false,color:C.warm,icon:DollarSign},
              {l:"Tickets Completed",v:sp.summary.tickets_completed.toString(),delta:`+${sp.summary.vs_previous.tickets} vs S41`,up:true,color:C.green,icon:GitCommit},
              {l:"Avg Cost per Ticket",v:`$${sp.summary.cost_per_ticket}`,delta:`$${sp.summary.vs_previous.cost_per_ticket} vs S41`,up:true,color:C.accent,icon:TrendingUp},
              {l:"Sprint AI ROI",v:`${sp.summary.roi_multiplier}x`,delta:"based on velocity",up:null,color:C.purple,icon:BarChart2},
            ].map((card,i)=>(
              <div key={i} style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:9,padding:"14px 16px"}}>
                <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:8}}>
                  <span style={{fontFamily:F.body,fontSize:10,color:C.sub,textTransform:"uppercase",letterSpacing:"0.06em"}}>{card.l}</span>
                  <div style={{width:24,height:24,borderRadius:6,background:`${card.color}15`,display:"flex",alignItems:"center",justifyContent:"center"}}>
                    <card.icon size={12} color={card.color}/>
                  </div>
                </div>
                <div style={{fontFamily:F.mono,fontSize:26,fontWeight:600,color:card.color,lineHeight:1,marginBottom:4}}>{card.v}</div>
                {card.up!==null?(
                  <div style={{fontFamily:F.mono,fontSize:10,color:card.up?C.green:C.red}}>{card.delta}</div>
                ):<div style={{fontFamily:F.body,fontSize:10,color:C.sub}}>{card.delta}</div>}
              </div>
            ))}
          </div>

          <div style={{display:"grid",gridTemplateColumns:"2fr 1fr",gap:14}}>
            {/* Daily spend chart */}
            <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:9,overflow:"hidden"}}>
              <div style={{padding:"12px 16px 9px"}}><div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text}}>Daily AI Spend</div><div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginTop:2}}>AI spend per day within Sprint 42</div></div>
              <Divider/>
              <div style={{padding:"10px 8px 8px"}}>
                <ResponsiveContainer width="100%" height={140}>
                  <BarChart data={sp.daily_spend} margin={{top:4,right:8,bottom:0,left:-16}}>
                    <XAxis dataKey="d" tick={{fontSize:9,fill:C.sub,fontFamily:F.body}} axisLine={false} tickLine={false}/>
                    <YAxis tick={{fontSize:9,fill:C.sub,fontFamily:F.body}} axisLine={false} tickLine={false} tickFormatter={v=>`$${v}`}/>
                    <Tooltip content={<CT/>}/>
                    <Bar dataKey="v" radius={[3,3,0,0]}>
                      {sp.daily_spend.map((_,i)=>(<Cell key={i} fill={C.warm} fillOpacity={_.v>40?0.85:_.v===0?0.1:0.5}/>))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
            {/* Dev spend distribution */}
            <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:9,overflow:"hidden"}}>
              <div style={{padding:"12px 16px 9px"}}><div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text}}>Developer Spend</div><div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginTop:2}}>% of sprint AI budget</div></div>
              <Divider/>
              <div style={{padding:"8px 0"}}>
                {sp.dev_spend.filter(d=>d.spend>0).map((d,i)=>(
                  <div key={i}>
                    <div style={{padding:"7px 14px"}}>
                      <div style={{display:"flex",justifyContent:"space-between",marginBottom:4}}>
                        <span style={{fontFamily:F.body,fontSize:11,color:C.text}}>{d.name}</span>
                        <div style={{display:"flex",gap:10}}>
                          <span style={{fontFamily:F.mono,fontSize:11,color:C.warm}}>${d.spend}</span>
                          <span style={{fontFamily:F.mono,fontSize:11,color:C.sub}}>{d.pct.toFixed(1)}%</span>
                        </div>
                      </div>
                      <div style={{height:4,background:C.muted,borderRadius:2,overflow:"hidden"}}>
                        <div style={{height:"100%",width:`${d.pct}%`,background:C.accent,borderRadius:2,opacity:0.65}}/>
                      </div>
                    </div>
                    {i<sp.dev_spend.filter(d=>d.spend>0).length-1&&<Divider/>}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Tickets table */}
          <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:9,overflow:"hidden"}}>
            <div style={{padding:"12px 16px 9px",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
              <div><div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text}}>Tickets</div><div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginTop:2}}>All tickets in Sprint 42 · click to drill into sessions</div></div>
            </div>
            <Divider/>
            <div style={{display:"grid",gridTemplateColumns:"100px 1fr 90px 80px 70px 80px 70px 70px",gap:8,padding:"6px 16px"}}>
              {["Ticket","Title","Developer","AI Cost","Sessions","AI Code%","Status","ROI"].map(h=>(
                <span key={h} style={{fontFamily:F.body,fontSize:10,color:C.sub,textTransform:"uppercase",letterSpacing:"0.06em",fontWeight:600}}>{h}</span>
              ))}
            </div>
            <Divider/>
            {sp.tickets.map((t,i)=>{
              const isAlert=t.risk==="alert";
              const statusCfg={done:{c:C.green,bg:C.greenBg},active:{c:C.accent,bg:C.accentBg},review:{c:C.amber,bg:C.amberBg}}[t.status]??{c:C.sub,bg:C.muted};
              const aiColor=t.ai_pct>=80?C.green:t.ai_pct>=60?C.amber:C.red;
              return(
                <div key={i}>
                  <div onMouseEnter={()=>setHov(t.id)} onMouseLeave={()=>setHov(null)}
                    style={{display:"grid",gridTemplateColumns:"100px 1fr 90px 80px 70px 80px 70px 70px",gap:8,padding:"11px 16px",alignItems:"center",background:hov===t.id?C.hover:isAlert?"rgba(255,69,69,0.03)":"transparent",cursor:"pointer",transition:"background .1s",borderLeft:isAlert?`3px solid ${C.red}`:"3px solid transparent"}}>
                    <span style={{fontFamily:F.mono,fontSize:11,color:C.accent}}>{t.id}</span>
                    <span style={{fontFamily:F.body,fontSize:12,color:C.text,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{t.title}</span>
                    <span style={{fontFamily:F.body,fontSize:11,color:C.sub}}>{t.dev}</span>
                    <span style={{fontFamily:F.mono,fontSize:12,fontWeight:600,color:t.cost>8?C.amber:C.text}}>${t.cost.toFixed(2)}</span>
                    <span style={{fontFamily:F.mono,fontSize:12,color:C.sub}}>{t.sessions}</span>
                    <span style={{fontFamily:F.mono,fontSize:12,fontWeight:600,color:aiColor}}>{t.ai_pct}%</span>
                    <Tag color={statusCfg.c} bg={statusCfg.bg}>{t.status}</Tag>
                    {t.roi!=null?<Tag color={t.roi>0?C.green:C.red} bg={t.roi>0?C.greenBg:C.redBg}>{t.roi>0?"+":""}{t.roi}x</Tag>:<span style={{fontFamily:F.body,fontSize:10,color:C.sub}}>in progress</span>}
                  </div>
                  {i<sp.tickets.length-1&&<Divider/>}
                </div>
              );
            })}
            <Divider/>
            <div style={{padding:"9px 16px",display:"flex",justifyContent:"space-between"}}>
              <span style={{fontFamily:F.body,fontSize:11,color:C.sub}}>Showing {sp.tickets.length} of {sp.sprint.tickets} tickets · 2 at risk</span>
              <span style={{fontFamily:F.body,fontSize:11,color:C.accent,cursor:"pointer"}}>View all →</span>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
