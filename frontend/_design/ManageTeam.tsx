/**
 * S-09 Settings — Manage Team
 * Team members list, invite, roles, agent status, hourly rates.
 * Access: Org Admin (all), Team Lead (own team).
 */

import { useState } from "react";
import { Plus, Send, MoreHorizontal, ChevronDown } from "lucide-react";

const C={bg:"#080808",card:"#101010",surface:"#181818",hover:"#1E1E1E",accent:"#00D4FF",accentBg:"rgba(0,212,255,0.08)",warm:"#FFB547",green:"#00E676",greenBg:"rgba(0,230,118,0.08)",red:"#FF4545",redBg:"rgba(255,69,69,0.08)",amber:"#FFB800",amberBg:"rgba(255,184,0,0.08)",purple:"#A78BFA",text:"#F0F0F0",sub:"#5A5A5A",muted:"#2E2E2E",border:"rgba(255,255,255,0.07)",borderHi:"rgba(255,255,255,0.14)"} as const;
const F={ui:"'Outfit',sans-serif",body:"'DM Sans',sans-serif",mono:"'JetBrains Mono',monospace"};

const MEMBERS=[
  {id:"m1",name:"Adnan K",email:"adnan@company.com",role:"org_admin",team:"Platform",avatar:"AK",avc:"#00D4FF",agent:"active",last_active:"Just now",hourly_rate:80},
  {id:"m2",name:"Sara P",email:"sara@company.com",role:"team_lead",team:"Platform",avatar:"SP",avc:"#A78BFA",agent:"active",last_active:"2h ago",hourly_rate:75},
  {id:"m3",name:"Raj K",email:"raj@company.com",role:"developer",team:"Platform",avatar:"RK",avc:"#00E676",agent:"active",last_active:"3h ago",hourly_rate:65},
  {id:"m4",name:"Priya M",email:"priya@company.com",role:"developer",team:"Frontend",avatar:"PM",avc:"#FFB547",agent:"active",last_active:"1d ago",hourly_rate:65},
  {id:"m5",name:"Vikram S",email:"vikram@company.com",role:"developer",team:"Platform",avatar:"VS",avc:"#FFB800",agent:"active",last_active:"2d ago",hourly_rate:60},
  {id:"m6",name:"Meera T",email:"meera@company.com",role:"developer",team:"Frontend",avatar:"MT",avc:"#5A5A5A",agent:"inactive",last_active:"5d ago",hourly_rate:60},
  {id:"m7",name:"Dev A",email:"dev.a@company.com",role:"developer",team:"Data",avatar:"DA",avc:"#5A5A5A",agent:"installed_no_session",last_active:"Never",hourly_rate:65},
  {id:"m8",name:"Kiran R",email:"kiran@company.com",role:"developer",team:"Data",avatar:"KR",avc:"#5A5A5A",agent:"not_installed",last_active:"Never",hourly_rate:60},
];

function Divider(){return <div style={{height:1,background:C.border}}/>;}
function Tag({children,color,bg}:any){
  return <span style={{padding:"2px 7px",borderRadius:4,background:bg,color,fontFamily:F.mono,fontSize:9,fontWeight:600}}>{children}</span>;
}

function AgentDot({status}:{status:string}){
  const cfg={
    active:{c:C.green,l:"Active"},
    inactive:{c:C.amber,l:"Inactive"},
    installed_no_session:{c:C.sub,l:"Installed"},
    not_installed:{c:C.red,l:"Not installed"},
  }[status]??{c:C.sub,l:status};
  return(
    <span style={{display:"flex",alignItems:"center",gap:5}}>
      <span style={{width:7,height:7,borderRadius:"50%",background:cfg.c,flexShrink:0}}/>
      <span style={{fontFamily:F.body,fontSize:11,color:C.sub}}>{cfg.l}</span>
    </span>
  );
}

function RoleBadge({role}:{role:string}){
  const cfg={
    org_admin:{c:C.accent,bg:C.accentBg,l:"Org Admin"},
    team_lead:{c:C.purple,bg:"rgba(167,139,250,0.08)",l:"Team Lead"},
    developer:{c:C.sub,bg:"rgba(90,90,90,0.1)",l:"Developer"},
  }[role]??{c:C.sub,bg:"transparent",l:role};
  return <Tag color={cfg.c} bg={cfg.bg}>{cfg.l}</Tag>;
}

export default function ManageTeam(){
  const [showInvite,setShowInvite]=useState(false);
  const [hov,setHov]=useState<string|null>(null);
  return(
    <>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=DM+Sans:opsz,wght@9..40,400;9..40,500&family=JetBrains+Mono:wght@400;500;600&display=swap');*{box-sizing:border-box;margin:0;padding:0}::-webkit-scrollbar{width:4px}::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:2px}input{font-family:'DM Sans',sans-serif}input::placeholder{color:#5A5A5A}`}</style>
      <div style={{minHeight:"100vh",background:C.bg,fontFamily:F.body,color:C.text}}>
        <div style={{borderBottom:`1px solid ${C.border}`,padding:"18px 28px 16px",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
          <div>
            <div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginBottom:4}}>Settings · Manage Team</div>
            <h1 style={{fontFamily:F.ui,fontSize:22,fontWeight:700,color:C.text,letterSpacing:"-0.02em"}}>Manage Team</h1>
            <div style={{fontFamily:F.body,fontSize:12,color:C.sub,marginTop:4}}>{MEMBERS.length} members · {MEMBERS.filter(m=>m.agent==="active").length} agents active</div>
          </div>
          <button onClick={()=>setShowInvite(true)} style={{background:C.accentBg,border:`1px solid rgba(0,212,255,0.3)`,borderRadius:7,padding:"8px 16px",cursor:"pointer",fontFamily:F.body,fontSize:12,color:C.accent,display:"flex",alignItems:"center",gap:7}}>
            <Plus size={13}/> Invite members
          </button>
        </div>
        <div style={{padding:"22px 28px"}}>
          <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:10,overflow:"hidden"}}>
            <div style={{display:"grid",gridTemplateColumns:"1fr 80px 100px 80px 90px 100px 80px 100px",gap:8,padding:"7px 18px"}}>
              {["Member","Role","Team","Agent","Last active","Hourly rate","Sessions","Actions"].map(h=>(
                <span key={h} style={{fontFamily:F.body,fontSize:10,color:C.sub,textTransform:"uppercase",letterSpacing:"0.06em",fontWeight:600}}>{h}</span>
              ))}
            </div>
            <Divider/>
            {MEMBERS.map((m,i)=>(
              <div key={m.id}>
                <div onMouseEnter={()=>setHov(m.id)} onMouseLeave={()=>setHov(null)}
                  style={{display:"grid",gridTemplateColumns:"1fr 80px 100px 80px 90px 100px 80px 100px",gap:8,padding:"11px 18px",alignItems:"center",background:hov===m.id?C.hover:"transparent",transition:"background .1s"}}>
                  <div style={{display:"flex",gap:10,alignItems:"center"}}>
                    <div style={{width:32,height:32,borderRadius:"50%",background:`${m.avc}15`,border:`1px solid ${m.avc}40`,display:"flex",alignItems:"center",justifyContent:"center",fontFamily:F.mono,fontSize:10,fontWeight:700,color:m.avc,flexShrink:0}}>{m.avatar}</div>
                    <div>
                      <div style={{fontFamily:F.body,fontSize:12,color:C.text,fontWeight:500}}>{m.name}</div>
                      <div style={{fontFamily:F.body,fontSize:10,color:C.sub}}>{m.email}</div>
                    </div>
                  </div>
                  <RoleBadge role={m.role}/>
                  <span style={{fontFamily:F.body,fontSize:11,color:C.sub}}>{m.team}</span>
                  <AgentDot status={m.agent}/>
                  <span style={{fontFamily:F.body,fontSize:11,color:C.sub}}>{m.last_active}</span>
                  <div style={{display:"flex",alignItems:"center",gap:5}}>
                    <span style={{fontFamily:F.mono,fontSize:12,color:m.hourly_rate?C.text:C.sub}}>{m.hourly_rate?`$${m.hourly_rate}/h`:"—"}</span>
                  </div>
                  <span style={{fontFamily:F.mono,fontSize:12,color:C.sub}}>—</span>
                  <div style={{display:"flex",gap:5}}>
                    {m.agent==="not_installed"&&(
                      <button style={{background:"none",border:`1px solid ${C.border}`,borderRadius:5,padding:"3px 8px",cursor:"pointer",fontFamily:F.body,fontSize:10,color:C.sub,display:"flex",alignItems:"center",gap:3}}>
                        <Send size={10}/> Resend
                      </button>
                    )}
                    <button style={{background:"none",border:`1px solid ${C.border}`,borderRadius:5,padding:"3px 6px",cursor:"pointer",color:C.sub}}>
                      <MoreHorizontal size={13}/>
                    </button>
                  </div>
                </div>
                {i<MEMBERS.length-1&&<Divider/>}
              </div>
            ))}
          </div>
        </div>
        {showInvite&&(
          <div onClick={()=>setShowInvite(false)} style={{position:"fixed",inset:0,background:"rgba(0,0,0,0.7)",display:"flex",alignItems:"center",justifyContent:"center",zIndex:200}}>
            <div onClick={e=>e.stopPropagation()} style={{background:C.card,border:`1px solid ${C.borderHi}`,borderRadius:11,width:440,overflow:"hidden",boxShadow:"0 24px 60px rgba(0,0,0,0.8)"}}>
              <div style={{padding:"14px 18px 12px",borderBottom:`1px solid ${C.border}`,display:"flex",justifyContent:"space-between"}}>
                <div style={{fontFamily:F.ui,fontSize:14,fontWeight:600,color:C.text}}>Invite team members</div>
                <button onClick={()=>setShowInvite(false)} style={{background:"none",border:"none",cursor:"pointer",color:C.sub,fontSize:18}}>✕</button>
              </div>
              <div style={{padding:"16px 18px"}}>
                <div style={{fontFamily:F.body,fontSize:12,color:C.sub,marginBottom:8}}>Paste emails or GitHub usernames (one per line)</div>
                <textarea rows={4} placeholder={"sara@company.com\nraj@company.com\ngithub_username"} style={{width:"100%",background:C.surface,border:`1px solid ${C.border}`,borderRadius:7,padding:"10px 12px",fontFamily:F.mono,fontSize:11,color:C.text,outline:"none",resize:"vertical"}}/>
                <div style={{display:"flex",gap:10,marginTop:12,alignItems:"center"}}>
                  <span style={{fontFamily:F.body,fontSize:12,color:C.sub}}>Default role:</span>
                  <select style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:6,padding:"5px 10px",fontFamily:F.body,fontSize:12,color:C.text,outline:"none",cursor:"pointer"}}>
                    <option>Developer</option><option>Team Lead</option>
                  </select>
                </div>
                <div style={{display:"flex",gap:8,marginTop:14,justifyContent:"flex-end"}}>
                  <button onClick={()=>setShowInvite(false)} style={{background:"none",border:`1px solid ${C.border}`,borderRadius:6,padding:"7px 14px",cursor:"pointer",fontFamily:F.body,fontSize:12,color:C.sub}}>Cancel</button>
                  <button onClick={()=>setShowInvite(false)} style={{background:C.accentBg,border:`1px solid rgba(0,212,255,0.3)`,borderRadius:6,padding:"7px 16px",cursor:"pointer",fontFamily:F.body,fontSize:12,color:C.accent,display:"flex",alignItems:"center",gap:6}}>
                    <Send size={12}/> Send invitations
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
