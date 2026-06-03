/**
 * S-07 My Activity
 * Developer's own sessions only. No comparison to teammates.
 * Access: ALL roles (only screen developers can see).
 *
 * REAL API CONTRACT:
 *   GET /api/v1/me/sessions?sprint_id=SPRINT-42
 *   GET /api/v1/me/summary
 */

import { useState } from "react";
import { Clock, DollarSign, GitBranch, Tag as TagIcon, ChevronDown, Zap, GitCommit } from "lucide-react";

const C={bg:"#080808",card:"#101010",surface:"#181818",hover:"#1E1E1E",accent:"#00D4FF",accentBg:"rgba(0,212,255,0.08)",warm:"#FFB547",warmBg:"rgba(255,181,71,0.08)",green:"#00E676",greenBg:"rgba(0,230,118,0.08)",red:"#FF4545",redBg:"rgba(255,69,69,0.08)",amber:"#FFB800",amberBg:"rgba(255,184,0,0.08)",purple:"#A78BFA",purpleBg:"rgba(167,139,250,0.08)",text:"#F0F0F0",sub:"#5A5A5A",muted:"#2E2E2E",border:"rgba(255,255,255,0.07)",borderHi:"rgba(255,255,255,0.14)"} as const;
const F={ui:"'Outfit',sans-serif",body:"'DM Sans',sans-serif",mono:"'JetBrains Mono',monospace"};

const MOCK_MY = {
  developer:{name:"Adnan K",avatar:"AK",color:"#00D4FF"},
  summary:{sessions_today:4,tokens_today:42800,sessions_week:18,cost_week:4.20,cost_month:14.80,ai_code_pct:84,efficiency_score:78},
  sessions:[
    {id:"s1",started_at:"2026-05-28T09:28:00Z",tool:"claude-code",model:"claude-sonnet-4-6",duration_min:74,cost_usd:0.42,branch:"feature/JIRA-142-payment-gateway",ticket_id:"JIRA-142",ticket_title:"Stripe payment gateway",confidence:0.87,is_committed:true,hallucination_risk:"none",lines_added:47,lines_accepted:38},
    {id:"s2",started_at:"2026-05-28T14:10:00Z",tool:"cursor",model:"claude-sonnet-4-6",duration_min:35,cost_usd:1.20,branch:"feature/JIRA-142-payment-gateway",ticket_id:"JIRA-142",ticket_title:"Stripe payment gateway",confidence:0.87,is_committed:false,hallucination_risk:"none",lines_added:28,lines_accepted:22},
    {id:"s3",started_at:"2026-05-27T10:00:00Z",tool:"claude-code",model:"claude-sonnet-4-6",duration_min:92,cost_usd:0.68,branch:"patch-2",ticket_id:null,ticket_title:null,confidence:0,is_committed:true,hallucination_risk:"watch",lines_added:82,lines_accepted:61},
    {id:"s4",started_at:"2026-05-27T15:30:00Z",tool:"claude-code",model:"claude-haiku-4",duration_min:28,cost_usd:0.12,branch:"feature/JIRA-155-auth-sso",ticket_id:"JIRA-155",ticket_title:"Auth SSO integration",confidence:0.92,is_committed:true,hallucination_risk:"none",lines_added:18,lines_accepted:16},
    {id:"s5",started_at:"2026-05-26T11:00:00Z",tool:"cursor",model:"gpt-4o",duration_min:55,cost_usd:1.80,branch:"feature/JIRA-155-auth-sso",ticket_id:"JIRA-155",ticket_title:"Auth SSO integration",confidence:0.92,is_committed:true,hallucination_risk:"none",lines_added:64,lines_accepted:54},
  ],
};

function Divider(){return <div style={{height:1,background:C.border}}/>;}
function Tag({children,color,bg}:any){
  return <span style={{padding:"2px 7px",borderRadius:4,background:bg,color,fontFamily:F.mono,fontSize:10,fontWeight:600}}>{children}</span>;
}
function timeAgo(iso:string){
  const h=Math.floor((Date.now()-new Date(iso).getTime())/3600000);
  return h<24?`${h}h ago`:`${Math.floor(h/24)}d ago`;
}

export default function MyActivity(){
  const [tagging,setTagging]=useState<string|null>(null);
  const [query,setQuery]=useState("");
  const d=MOCK_MY;
  const s=d.summary;

  const tickets=[
    {id:"JIRA-142",t:"Stripe payment gateway"},{id:"JIRA-151",t:"Data pipeline refactor"},
    {id:"JIRA-155",t:"Auth SSO integration"},{id:"JIRA-159",t:"Search & filter API"},
    {id:"JIRA-163",t:"Mobile push notifications"},
  ];

  return(
    <>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=DM+Sans:opsz,wght@9..40,400;9..40,500&family=JetBrains+Mono:wght@400;500;600&display=swap');*{box-sizing:border-box;margin:0;padding:0}::-webkit-scrollbar{width:4px}::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:2px}input{font-family:'DM Sans',sans-serif}input::placeholder{color:#5A5A5A}`}</style>
      <div style={{minHeight:"100vh",background:C.bg,fontFamily:F.body,color:C.text}}>
        <div style={{borderBottom:`1px solid ${C.border}`,padding:"18px 28px 16px",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
          <div>
            <div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginBottom:4}}>My Activity</div>
            <h1 style={{fontFamily:F.ui,fontSize:22,fontWeight:700,color:C.text,letterSpacing:"-0.02em"}}>My AI Sessions</h1>
            <div style={{fontFamily:F.body,fontSize:12,color:C.sub,marginTop:4}}>Your personal AI usage — only you can see this data</div>
          </div>
          <div style={{display:"flex",alignItems:"center",gap:10}}>
            <div style={{width:36,height:36,borderRadius:"50%",background:`${d.developer.color}15`,border:`2px solid ${d.developer.color}40`,display:"flex",alignItems:"center",justifyContent:"center",fontFamily:F.mono,fontSize:12,fontWeight:700,color:d.developer.color}}>{d.developer.avatar}</div>
            <div>
              <div style={{fontFamily:F.body,fontSize:13,color:C.text,fontWeight:500}}>{d.developer.name}</div>
              <div style={{fontFamily:F.body,fontSize:11,color:C.sub}}>Developer</div>
            </div>
          </div>
        </div>
        <div style={{padding:"22px 28px",display:"flex",flexDirection:"column",gap:14}}>
          {/* Summary strip */}
          <div style={{display:"grid",gridTemplateColumns:"repeat(5,1fr)",gap:10}}>
            {[
              {l:"Sessions today",v:s.sessions_today.toString(),color:C.accent},
              {l:"Tokens today",v:`${(s.tokens_today/1000).toFixed(1)}k`,color:C.purple},
              {l:"Sessions this week",v:s.sessions_week.toString(),color:C.text},
              {l:"Cost this week",v:`$${s.cost_week.toFixed(2)}`,color:C.warm},
              {l:"AI code acceptance",v:`${s.ai_code_pct}%`,color:C.green},
            ].map((item,i)=>(
              <div key={i} style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:9,padding:"13px 15px"}}>
                <div style={{fontFamily:F.body,fontSize:10,color:C.sub,textTransform:"uppercase",letterSpacing:"0.06em",marginBottom:5}}>{item.l}</div>
                <div style={{fontFamily:F.mono,fontSize:22,fontWeight:600,color:item.color,lineHeight:1}}>{item.v}</div>
              </div>
            ))}
          </div>

          {/* Privacy note */}
          <div style={{background:C.accentBg,border:`1px solid rgba(0,212,255,0.12)`,borderRadius:9,padding:"10px 16px",display:"flex",alignItems:"center",gap:10}}>
            <Zap size={13} color={C.accent}/>
            <span style={{fontFamily:F.body,fontSize:12,color:C.sub}}>This page shows only your own sessions. Team leads and managers can see aggregate team metrics, but not this individual view.</span>
          </div>

          {/* Session list */}
          <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:10,overflow:"hidden"}}>
            <div style={{padding:"14px 18px 10px",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
              <div>
                <div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text}}>Session History</div>
                <div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginTop:2}}>Your AI sessions — last 7 days</div>
              </div>
              <button style={{background:"none",border:`1px solid ${C.border}`,borderRadius:6,padding:"5px 11px",cursor:"pointer",fontFamily:F.body,fontSize:11,color:C.sub,display:"flex",alignItems:"center",gap:5}}>Last 7 days <ChevronDown size={11}/></button>
            </div>
            <Divider/>
            <div style={{display:"grid",gridTemplateColumns:"110px 80px 80px 1fr 80px 80px 70px 80px",gap:8,padding:"6px 18px"}}>
              {["Time","Tool","Duration","Ticket","Cost","Lines","Quality","Status"].map(h=>(
                <span key={h} style={{fontFamily:F.body,fontSize:10,color:C.sub,textTransform:"uppercase",letterSpacing:"0.06em",fontWeight:600}}>{h}</span>
              ))}
            </div>
            <Divider/>
            {d.sessions.map((sess,i)=>{
              const riskColor=sess.hallucination_risk==="alert"?C.red:sess.hallucination_risk==="watch"?C.amber:C.green;
              const riskBg=sess.hallucination_risk==="alert"?C.redBg:sess.hallucination_risk==="watch"?C.amberBg:C.greenBg;
              return(
                <div key={i}>
                  <div style={{display:"grid",gridTemplateColumns:"110px 80px 80px 1fr 80px 80px 70px 80px",gap:8,padding:"11px 18px",alignItems:"center"}}>
                    <div>
                      <div style={{fontFamily:F.mono,fontSize:10,color:C.sub}}>{timeAgo(sess.started_at)}</div>
                      <div style={{fontFamily:F.mono,fontSize:10,color:C.sub,marginTop:1}}>{new Date(sess.started_at).toLocaleTimeString("en-GB",{hour:"2-digit",minute:"2-digit"})}</div>
                    </div>
                    <span style={{fontFamily:F.mono,fontSize:10,color:sess.tool==="claude-code"?C.accent:C.purple}}>{sess.tool==="claude-code"?"CC":"Cursor"}</span>
                    <span style={{fontFamily:F.mono,fontSize:11,color:C.sub}}>{sess.duration_min}min</span>
                    <div>
                      {sess.ticket_id?(
                        <div>
                          <div style={{fontFamily:F.mono,fontSize:11,color:C.accent}}>{sess.ticket_id}</div>
                          <div style={{fontFamily:F.body,fontSize:10,color:C.sub,marginTop:1,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{sess.ticket_title}</div>
                        </div>
                      ):(
                        <button onClick={()=>setTagging(sess.id)} style={{background:C.amberBg,border:`1px solid rgba(255,184,0,0.2)`,borderRadius:5,padding:"3px 9px",cursor:"pointer",fontFamily:F.body,fontSize:11,color:C.amber,display:"flex",alignItems:"center",gap:4}}>
                          <TagIcon size={10}/> Tag session
                        </button>
                      )}
                    </div>
                    <span style={{fontFamily:F.mono,fontSize:12,fontWeight:600,color:C.warm}}>${sess.cost_usd.toFixed(2)}</span>
                    <span style={{fontFamily:F.mono,fontSize:11,color:C.sub}}>+{sess.lines_added} / {sess.lines_accepted}✓</span>
                    <Tag color={riskColor} bg={riskBg}>{sess.hallucination_risk}</Tag>
                    {sess.is_committed
                      ?<Tag color={C.green} bg={C.greenBg}>Committed</Tag>
                      :<Tag color={C.sub} bg={C.muted}>Pending</Tag>}
                  </div>
                  {i<d.sessions.length-1&&<Divider/>}
                </div>
              );
            })}
          </div>
        </div>

        {/* Tag modal */}
        {tagging&&(
          <div onClick={()=>setTagging(null)} style={{position:"fixed",inset:0,background:"rgba(0,0,0,0.7)",display:"flex",alignItems:"center",justifyContent:"center",zIndex:200}}>
            <div onClick={e=>e.stopPropagation()} style={{background:C.card,border:`1px solid ${C.borderHi}`,borderRadius:11,width:420,overflow:"hidden",boxShadow:"0 24px 60px rgba(0,0,0,0.8)"}}>
              <div style={{padding:"14px 18px 12px",borderBottom:`1px solid ${C.border}`,display:"flex",justifyContent:"space-between",alignItems:"center"}}>
                <div style={{fontFamily:F.ui,fontSize:14,fontWeight:600,color:C.text}}>Tag this session</div>
                <button onClick={()=>setTagging(null)} style={{background:"none",border:"none",cursor:"pointer",color:C.sub,fontSize:18}}>✕</button>
              </div>
              <div style={{padding:"10px 18px",borderBottom:`1px solid ${C.border}`}}>
                <input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search your tickets..." autoFocus
                  style={{width:"100%",background:C.surface,border:`1px solid ${C.border}`,borderRadius:7,padding:"7px 12px",fontSize:12,color:C.text,outline:"none"}}/>
              </div>
              <div style={{maxHeight:240,overflowY:"auto"}}>
                {tickets.filter(t=>t.id.toLowerCase().includes(query.toLowerCase())||t.t.toLowerCase().includes(query.toLowerCase())).map((t,i)=>(
                  <div key={i} onClick={()=>setTagging(null)} style={{padding:"10px 18px",cursor:"pointer",display:"flex",justifyContent:"space-between",alignItems:"center"}}
                    onMouseEnter={e=>(e.currentTarget.style.background=C.hover)} onMouseLeave={e=>(e.currentTarget.style.background="transparent")}>
                    <div><span style={{fontFamily:F.mono,fontSize:11,color:C.accent}}>{t.id}</span><span style={{fontFamily:F.body,fontSize:12,color:C.text,marginLeft:10}}>{t.t}</span></div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
