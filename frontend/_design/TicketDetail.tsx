/**
 * S-14 Ticket Detail Drill-Down
 * Every AI session attributed to one ticket.
 * Reached from: Sprint detail → click ticket.
 *
 * REAL API CONTRACT:
 *   GET /api/v1/tickets/:ticketId
 *   GET /api/v1/tickets/:ticketId/sessions
 */

import { useState } from "react";
import { ArrowLeft, GitCommit, Clock, DollarSign, ChevronRight, AlertTriangle, CheckCircle2, XCircle } from "lucide-react";

const C={bg:"#080808",card:"#101010",surface:"#181818",hover:"#1E1E1E",accent:"#00D4FF",accentBg:"rgba(0,212,255,0.08)",warm:"#FFB547",warmBg:"rgba(255,181,71,0.08)",green:"#00E676",greenBg:"rgba(0,230,118,0.08)",red:"#FF4545",redBg:"rgba(255,69,69,0.08)",amber:"#FFB800",amberBg:"rgba(255,184,0,0.08)",purple:"#A78BFA",text:"#F0F0F0",sub:"#5A5A5A",muted:"#2E2E2E",border:"rgba(255,255,255,0.07)",borderHi:"rgba(255,255,255,0.14)"} as const;
const F={ui:"'Outfit',sans-serif",body:"'DM Sans',sans-serif",mono:"'JetBrains Mono',monospace"};

const MOCK_TICKET = {
  ticket:{id:"JIRA-142",title:"Implement Stripe payment gateway",status:"done",assignee:"Adnan K",epic:{id:"EPIC-12",name:"Checkout & Payments"},sprint:"Sprint 42",story_points:8,created_at:"2026-05-15",closed_at:"2026-05-28"},
  attribution:{confidence:0.87,signals:["branch_match","file_overlap","temporal_proximity"],method:"branch_parse"},
  cost_summary:{total_ai_cost:4.20,sessions:3,total_ai_hours:3.05,human_hours:2.5,human_rate:80,true_cost:404.20,lines_ai:159,lines_accepted:127,lines_reverted:32},
  timeline:[
    {event:"First AI session",time:"May 27, 09:28",type:"session"},
    {event:"First commit",time:"May 27, 10:55",type:"commit"},
    {event:"Session 2",time:"May 27, 14:10",type:"session"},
    {event:"Second commit",time:"May 27, 15:42",type:"commit"},
    {event:"PR opened",time:"May 28, 09:00",type:"pr"},
    {event:"PR reviewed",time:"May 28, 11:30",type:"review"},
    {event:"PR merged",time:"May 28, 14:20",type:"merge"},
  ],
  sessions:[
    {id:"s1",date:"May 28",dev:"Adnan K",tool:"Claude Code",model:"claude-sonnet-4-6",duration_min:74,cost:0.42,mode:"agent",quality:"none",branch:"feature/JIRA-142-payment-gateway",committed:true,lines_added:47,lines_accepted:38},
    {id:"s2",date:"May 27",dev:"Adnan K",tool:"Claude Code",model:"claude-sonnet-4-6",duration_min:92,cost:0.68,mode:"agent",quality:"watch",branch:"feature/JIRA-142-payment-gateway",committed:true,lines_added:82,lines_accepted:61},
    {id:"s3",date:"May 27",dev:"Adnan K",tool:"Cursor",model:"claude-sonnet-4-6",duration_min:29,cost:0.12,mode:"chat",quality:"none",branch:"feature/JIRA-142-payment-gateway",committed:false,lines_added:30,lines_accepted:28},
  ],
};

function Divider(){return <div style={{height:1,background:C.border}}/>;}
function Tag({children,color,bg}:any){
  return <span style={{padding:"2px 7px",borderRadius:4,background:bg,color,fontFamily:F.mono,fontSize:10,fontWeight:600}}>{children}</span>;
}

export default function TicketDetail(){
  const [hov,setHov]=useState<string|null>(null);
  const t=MOCK_TICKET;
  const signals:{[k:string]:string}={branch_match:"Branch matched ticket ID",file_overlap:"Files touched match ticket PR",temporal_proximity:"Session active while ticket In Progress",developer_match:"Developer = assignee",explicit_mention:"Ticket ID in commit message"};

  return(
    <>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=DM+Sans:opsz,wght@9..40,400;9..40,500&family=JetBrains+Mono:wght@400;500;600&display=swap');*{box-sizing:border-box;margin:0;padding:0}::-webkit-scrollbar{width:4px}::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:2px}`}</style>
      <div style={{minHeight:"100vh",background:C.bg,fontFamily:F.body,color:C.text}}>
        <div style={{borderBottom:`1px solid ${C.border}`,padding:"12px 28px",display:"flex",alignItems:"center",gap:10}}>
          <button style={{background:"none",border:"none",cursor:"pointer",color:C.sub,display:"flex",alignItems:"center",gap:5,fontFamily:F.body,fontSize:12}}><ArrowLeft size={14}/> Sprint 42</button>
          <span style={{color:C.muted}}>·</span>
          <span style={{fontFamily:F.mono,fontSize:12,color:C.accent}}>JIRA-142</span>
        </div>

        <div style={{borderBottom:`1px solid ${C.border}`,padding:"16px 28px"}}>
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start"}}>
            <div>
              <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:5}}>
                <span style={{fontFamily:F.mono,fontSize:14,color:C.accent}}>JIRA-142</span>
                <Tag color={C.green} bg={C.greenBg}>Done</Tag>
                <Tag color={C.sub} bg="rgba(90,90,90,0.1)">{t.ticket.sprint}</Tag>
              </div>
              <h1 style={{fontFamily:F.ui,fontSize:20,fontWeight:700,color:C.text,letterSpacing:"-0.02em",marginBottom:6}}>{t.ticket.title}</h1>
              <div style={{fontFamily:F.body,fontSize:12,color:C.sub}}>
                Assignee: {t.ticket.assignee} · Epic: {t.ticket.epic.name} · {t.ticket.story_points}pt
              </div>
            </div>
            <div style={{display:"flex",gap:8,alignItems:"center"}}>
              <Tag color={t.attribution.confidence>=0.8?C.green:C.amber} bg={t.attribution.confidence>=0.8?C.greenBg:C.amberBg}>
                {Math.round(t.attribution.confidence*100)}% attributed
              </Tag>
              <button style={{background:"none",border:`1px solid ${C.border}`,borderRadius:6,padding:"5px 11px",cursor:"pointer",fontFamily:F.body,fontSize:11,color:C.sub}}>Reassign</button>
            </div>
          </div>
        </div>

        <div style={{padding:"22px 28px",display:"flex",flexDirection:"column",gap:14}}>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:14}}>
            {/* Cost summary */}
            <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:9,padding:"16px"}}>
              <div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text,marginBottom:14}}>Cost Summary</div>
              <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10,marginBottom:14}}>
                {[
                  {l:"AI Token Cost",v:`$${t.cost_summary.total_ai_cost.toFixed(2)}`,c:C.warm},
                  {l:"Human Time Cost",v:`$${(t.cost_summary.human_hours*t.cost_summary.human_rate).toFixed(0)}`,c:C.sub},
                  {l:"Lines AI-generated",v:t.cost_summary.lines_ai.toString(),c:C.text},
                  {l:"Lines Accepted",v:t.cost_summary.lines_accepted.toString(),c:C.green},
                ].map((s,i)=>(
                  <div key={i} style={{background:C.surface,borderRadius:7,padding:"10px 12px"}}>
                    <div style={{fontFamily:F.body,fontSize:10,color:C.sub,marginBottom:4}}>{s.l}</div>
                    <div style={{fontFamily:F.mono,fontSize:18,fontWeight:600,color:s.c}}>{s.v}</div>
                  </div>
                ))}
              </div>
              <div style={{background:C.warmBg,border:`1px solid rgba(255,181,71,0.2)`,borderRadius:8,padding:"10px 14px",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
                <span style={{fontFamily:F.body,fontSize:12,color:C.text,fontWeight:500}}>True total cost</span>
                <span style={{fontFamily:F.mono,fontSize:18,fontWeight:700,color:C.warm}}>${t.cost_summary.true_cost.toFixed(2)}</span>
              </div>
              <div style={{fontFamily:F.body,fontSize:10,color:C.sub,marginTop:6,textAlign:"center"}}>
                AI tokens + {t.cost_summary.human_hours}h × ${t.cost_summary.human_rate}/h developer time
              </div>
            </div>

            {/* Timeline */}
            <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:9,padding:"16px"}}>
              <div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text,marginBottom:14}}>Lifecycle Timeline</div>
              <div style={{position:"relative",paddingLeft:20}}>
                <div style={{position:"absolute",left:7,top:8,bottom:8,width:1,background:C.muted}}/>
                {t.timeline.map((ev,i)=>{
                  const dotColor={session:C.accent,commit:C.green,pr:C.purple,review:C.amber,merge:C.green}[ev.type]??C.sub;
                  return(
                    <div key={i} style={{display:"flex",alignItems:"flex-start",gap:12,marginBottom:i<t.timeline.length-1?14:0,position:"relative"}}>
                      <div style={{width:14,height:14,borderRadius:"50%",background:dotColor,border:`2px solid ${C.bg}`,flexShrink:0,marginTop:1,position:"absolute",left:-14}}/>
                      <div style={{paddingLeft:4}}>
                        <div style={{fontFamily:F.body,fontSize:12,color:C.text}}>{ev.event}</div>
                        <div style={{fontFamily:F.mono,fontSize:10,color:C.sub,marginTop:1}}>{ev.time}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Attribution signals */}
          <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:9,padding:"14px 16px"}}>
            <div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text,marginBottom:10}}>Attribution Signals</div>
            <div style={{display:"flex",gap:10,flexWrap:"wrap"}}>
              {Object.keys(signals).map((s,i)=>{
                const fired=t.attribution.signals.includes(s);
                return(
                  <div key={i} style={{display:"flex",alignItems:"center",gap:6,padding:"6px 12px",background:fired?C.accentBg:C.surface,border:`1px solid ${fired?"rgba(0,212,255,0.15)":C.border}`,borderRadius:7,opacity:fired?1:0.45}}>
                    {fired?<CheckCircle2 size={12} color={C.green}/>:<XCircle size={12} color={C.sub}/>}
                    <span style={{fontFamily:F.body,fontSize:11,color:fired?C.text:C.sub}}>{signals[s]}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Sessions table */}
          <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:9,overflow:"hidden"}}>
            <div style={{padding:"12px 16px 9px"}}><div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text}}>AI Sessions</div><div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginTop:2}}>All sessions attributed to JIRA-142 · click to view session detail</div></div>
            <Divider/>
            <div style={{display:"grid",gridTemplateColumns:"60px 80px 90px 80px 80px 70px 70px 70px 80px",gap:8,padding:"6px 16px"}}>
              {["Date","Developer","Tool","Duration","Cost","Mode","Quality","Lines","Status"].map(h=>(
                <span key={h} style={{fontFamily:F.body,fontSize:10,color:C.sub,textTransform:"uppercase",letterSpacing:"0.06em",fontWeight:600}}>{h}</span>
              ))}
            </div>
            <Divider/>
            {t.sessions.map((sess,i)=>{
              const rc=sess.quality==="alert"?C.red:sess.quality==="watch"?C.amber:C.green;
              const rb=sess.quality==="alert"?C.redBg:sess.quality==="watch"?C.amberBg:C.greenBg;
              return(
                <div key={i}>
                  <div onMouseEnter={()=>setHov(sess.id)} onMouseLeave={()=>setHov(null)}
                    style={{display:"grid",gridTemplateColumns:"60px 80px 90px 80px 80px 70px 70px 70px 80px",gap:8,padding:"11px 16px",alignItems:"center",background:hov===sess.id?C.hover:"transparent",cursor:"pointer",transition:"background .1s"}}>
                    <span style={{fontFamily:F.body,fontSize:11,color:C.sub}}>{sess.date}</span>
                    <span style={{fontFamily:F.body,fontSize:11,color:C.sub}}>{sess.dev}</span>
                    <span style={{fontFamily:F.mono,fontSize:10,color:C.sub}}>{sess.tool}</span>
                    <span style={{fontFamily:F.mono,fontSize:11,color:C.sub}}>{sess.duration_min}min</span>
                    <span style={{fontFamily:F.mono,fontSize:12,fontWeight:600,color:C.warm}}>${sess.cost.toFixed(2)}</span>
                    <Tag color={sess.mode==="agent"?C.accent:C.purple} bg={sess.mode==="agent"?C.accentBg:C.purpleBg}>{sess.mode}</Tag>
                    <Tag color={rc} bg={rb}>{sess.quality||"none"}</Tag>
                    <span style={{fontFamily:F.mono,fontSize:11,color:C.sub}}>+{sess.lines_added}/{sess.lines_accepted}✓</span>
                    {sess.committed?<Tag color={C.green} bg={C.greenBg}>Committed</Tag>:<Tag color={C.sub} bg={C.muted}>Pending</Tag>}
                  </div>
                  {i<t.sessions.length-1&&<Divider/>}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </>
  );
}
