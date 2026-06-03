/**
 * S-16 Hallucination Alerts Detail
 * Active and recent hallucination loop detections.
 *
 * REAL API CONTRACT:
 *   GET /api/v1/alerts?status=active&team_id=all
 *   PATCH /api/v1/alerts/:alert_id { status: "resolved" }
 */

import { useState } from "react";
import { AlertTriangle, CheckCircle2, ChevronDown, MessageSquare, Eye } from "lucide-react";

const C={bg:"#080808",card:"#101010",surface:"#181818",hover:"#1E1E1E",accent:"#00D4FF",accentBg:"rgba(0,212,255,0.08)",warm:"#FFB547",green:"#00E676",greenBg:"rgba(0,230,118,0.08)",red:"#FF4545",redBg:"rgba(255,69,69,0.08)",amber:"#FFB800",amberBg:"rgba(255,184,0,0.08)",text:"#F0F0F0",sub:"#5A5A5A",muted:"#2E2E2E",border:"rgba(255,255,255,0.07)",borderHi:"rgba(255,255,255,0.14)"} as const;
const F={ui:"'Outfit',sans-serif",body:"'DM Sans',sans-serif",mono:"'JetBrains Mono',monospace"};

const MOCK_ALERTS = [
  {id:"al1",dev:"Sara P",ticket:"JIRA-151",msg:"7 sessions, no commit in 3h · $8.40 spent",time:"42m ago",signals:["No commit >90min","Token spike at turn 9"],level:"high",status:"active"},
  {id:"al2",dev:"Adnan K",ticket:"JIRA-167",msg:"Token spike 4× avg at turn 9",time:"2h ago",signals:["Token spike detected"],level:"medium",status:"active"},
  {id:"al3",dev:"Raj K",ticket:"JIRA-155",msg:"3 restarts in 4h window",time:"2d ago",signals:["Session restarts >3"],level:"medium",status:"resolved",resolution:"Resolved — developer found syntax issue"},
  {id:"al4",dev:"Vikram S",ticket:"JIRA-159",msg:"Same file modified 6× in 2h",time:"3d ago",signals:["File oscillation"],level:"medium",status:"resolved",resolution:"Marked as exploratory refactor"},
];

function Divider(){return <div style={{height:1,background:C.border}}/>;}
function Tag({children,color,bg}:any){
  return <span style={{padding:"2px 7px",borderRadius:4,background:bg,color,fontFamily:F.mono,fontSize:10,fontWeight:600}}>{children}</span>;
}

export default function AlertsDetail(){
  const [alerts,setAlerts]=useState(MOCK_ALERTS);
  const resolve=(id:string)=>setAlerts(prev=>prev.map(a=>a.id===id?{...a,status:"resolved",resolution:"Marked resolved by team lead"}:a));
  const active=alerts.filter(a=>a.status==="active");
  const resolved=alerts.filter(a=>a.status==="resolved");

  return(
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=DM+Sans:opsz,wght@9..40,400;9..40,500&family=JetBrains+Mono:wght@400;500;600&display=swap');
        *{box-sizing:border-box;margin:0;padding:0}::-webkit-scrollbar{width:4px}::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:2px}
      `}</style>
      <div style={{minHeight:"100vh",background:C.bg,fontFamily:F.body,color:C.text}}>
        <div style={{borderBottom:`1px solid ${C.border}`,padding:"18px 28px 16px",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
          <div>
            <div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginBottom:4}}>Management · Alerts</div>
            <h1 style={{fontFamily:F.ui,fontSize:22,fontWeight:700,color:C.text,letterSpacing:"-0.02em"}}>Hallucination Alerts</h1>
            <div style={{fontFamily:F.body,fontSize:12,color:C.sub,marginTop:4}}>Active and recent loop detections across the team</div>
          </div>
          <div style={{display:"flex",gap:8}}>
            <button style={{background:"none",border:`1px solid ${C.border}`,borderRadius:7,padding:"7px 14px",cursor:"pointer",fontFamily:F.body,fontSize:12,color:C.sub,display:"flex",alignItems:"center",gap:6}}>All developers <ChevronDown size={12}/></button>
            <button style={{background:"none",border:`1px solid ${C.border}`,borderRadius:7,padding:"7px 14px",cursor:"pointer",fontFamily:F.body,fontSize:12,color:C.sub,display:"flex",alignItems:"center",gap:6}}>Last 7 days <ChevronDown size={12}/></button>
          </div>
        </div>
        <div style={{padding:"22px 28px",display:"flex",flexDirection:"column",gap:14}}>
          {/* Thresholds */}
          <div style={{background:C.amberBg,border:`1px solid rgba(255,184,0,0.15)`,borderRadius:10,padding:"14px 18px"}}>
            <div style={{fontFamily:F.body,fontSize:12,color:C.text,fontWeight:500,marginBottom:10}}>Alert thresholds</div>
            <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:10}}>
              {[{l:"Token spike",v:">3× session avg"},{l:"File oscillations",v:"same file >5× / 2h"},{l:"Session restarts",v:">3 / 4h window"},{l:"No commit",v:">90min no commit"}].map((t,i)=>(
                <div key={i} style={{background:C.surface,borderRadius:7,padding:"9px 12px"}}>
                  <div style={{fontFamily:F.body,fontSize:10,color:C.sub,marginBottom:3}}>{t.l}</div>
                  <div style={{fontFamily:F.mono,fontSize:11,color:C.amber}}>{t.v}</div>
                </div>
              ))}
            </div>
          </div>
          {/* Active */}
          <div style={{background:C.card,border:`1px solid rgba(255,69,69,0.2)`,borderRadius:10,overflow:"hidden"}}>
            <div style={{padding:"14px 18px 10px",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
              <div style={{display:"flex",alignItems:"center",gap:8}}>
                <AlertTriangle size={15} color={C.red}/>
                <div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text}}>Active Alerts</div>
              </div>
              <Tag color={C.red} bg={C.redBg}>{active.length} active</Tag>
            </div>
            <Divider/>
            {active.length===0?(<div style={{padding:"32px",textAlign:"center",fontFamily:F.body,fontSize:13,color:C.sub}}>No active alerts ✓</div>):
            active.map((a,i)=>(
              <div key={a.id}>
                <div style={{padding:"14px 18px"}}>
                  <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:8}}>
                    <div>
                      <span style={{fontFamily:F.mono,fontSize:12,color:a.level==="high"?C.red:C.amber}}>{a.dev}</span>
                      <span style={{fontFamily:F.mono,fontSize:12,color:C.accent,marginLeft:10}}>{a.ticket}</span>
                    </div>
                    <span style={{fontFamily:F.body,fontSize:11,color:C.sub}}>{a.time}</span>
                  </div>
                  <div style={{fontFamily:F.body,fontSize:12,color:C.sub,marginBottom:10}}>{a.msg}</div>
                  <div style={{display:"flex",gap:6,flexWrap:"wrap",marginBottom:11}}>
                    {a.signals.map((s,si)=>(
                      <Tag key={si} color={a.level==="high"?C.red:C.amber} bg={a.level==="high"?C.redBg:C.amberBg}>{s}</Tag>
                    ))}
                  </div>
                  <div style={{display:"flex",gap:7}}>
                    <button style={{background:"none",border:`1px solid ${C.border}`,borderRadius:6,padding:"5px 12px",cursor:"pointer",fontFamily:F.body,fontSize:11,color:C.sub,display:"flex",alignItems:"center",gap:5}}>
                      <Eye size={12}/> View session
                    </button>
                    <button style={{background:"none",border:`1px solid ${C.border}`,borderRadius:6,padding:"5px 12px",cursor:"pointer",fontFamily:F.body,fontSize:11,color:C.sub,display:"flex",alignItems:"center",gap:5}}>
                      <MessageSquare size={12}/> DM developer
                    </button>
                    <button onClick={()=>resolve(a.id)} style={{background:C.greenBg,border:`1px solid rgba(0,230,118,0.3)`,borderRadius:6,padding:"5px 12px",cursor:"pointer",fontFamily:F.body,fontSize:11,color:C.green,display:"flex",alignItems:"center",gap:5}}>
                      <CheckCircle2 size={12}/> Mark resolved
                    </button>
                  </div>
                </div>
                {i<active.length-1&&<Divider/>}
              </div>
            ))}
          </div>
          {/* Resolved */}
          {resolved.length>0&&(
            <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:10,overflow:"hidden"}}>
              <div style={{padding:"14px 18px 10px"}}><div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text}}>Recent — Last 7 Days</div></div>
              <Divider/>
              {resolved.map((a,i)=>(
                <div key={a.id}>
                  <div style={{padding:"13px 18px",opacity:0.7}}>
                    <div style={{display:"flex",justifyContent:"space-between",marginBottom:5}}>
                      <span style={{fontFamily:F.body,fontSize:12,color:C.text}}>{a.dev} · <span style={{fontFamily:F.mono,color:C.accent,fontSize:11}}>{a.ticket}</span></span>
                      <span style={{fontFamily:F.body,fontSize:11,color:C.sub}}>{a.time}</span>
                    </div>
                    <div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginBottom:4}}>{a.msg}</div>
                    <div style={{fontFamily:F.body,fontSize:11,color:C.green}}>✓ {a.resolution}</div>
                  </div>
                  {i<resolved.length-1&&<Divider/>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
