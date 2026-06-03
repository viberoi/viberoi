/**
 * S-06 Unknown Attribution Queue
 * Manager UI to assign, ignore, or mark unattributed sessions.
 * Access: Org Admin + Team Lead only.
 *
 * REAL API CONTRACT:
 *   GET  /api/v1/queue/unknown?status=pending&team_id=all
 *   PATCH /api/v1/queue/:session_id  { ticket_id, action }
 *   DELETE /api/v1/queue/:session_id { action: "ignore"|"exploratory" }
 *
 *   Coding agent: replace MOCK_QUEUE + inline handlers with real API calls
 */

import { useState, useRef } from "react";
import {
  Search, Filter, GitBranch, Clock, DollarSign,
  CheckCircle2, X, ChevronDown, AlertTriangle,
  Tag as TagIcon, ChevronRight, MoreHorizontal,
  Sparkles,
} from "lucide-react";

/* ─── Tokens ─────────────────────────────────────────────── */
const C = {
  bg:"#080808",card:"#101010",surface:"#181818",hover:"#1E1E1E",
  accent:"#00D4FF",accentBg:"rgba(0,212,255,0.08)",
  warm:"#FFB547",warmBg:"rgba(255,181,71,0.08)",
  green:"#00E676",greenBg:"rgba(0,230,118,0.08)",
  red:"#FF4545",redBg:"rgba(255,69,69,0.08)",
  amber:"#FFB800",amberBg:"rgba(255,184,0,0.08)",
  purple:"#A78BFA",
  text:"#F0F0F0",sub:"#5A5A5A",muted:"#2E2E2E",
  border:"rgba(255,255,255,0.07)",borderHi:"rgba(255,255,255,0.14)",
} as const;

const F = {
  ui:"'Outfit', sans-serif",
  body:"'DM Sans', sans-serif",
  mono:"'JetBrains Mono', monospace",
};

/* ─── Types ──────────────────────────────────────────────── */
type QueueStatus = "pending" | "assigned" | "ignored" | "exploratory";

interface QueueSession {
  session_id:    string;
  developer:     string;
  tool:          string;
  branch:        string;
  duration_min:  number;
  cost_usd:      number;
  started_at:    string;
  status:        QueueStatus;
  suggestion:    { ticket_id: string; title: string; confidence: number } | null;
  files_touched: string[];
}

/* ─── Mock Data (matches real API shape) ─────────────────── */
// GET /api/v1/queue/unknown
const MOCK_QUEUE: QueueSession[] = [
  { session_id:"q1", developer:"Adnan K",  tool:"Claude Code", branch:"patch-2",          duration_min:74,  cost_usd:0.42, started_at:"2026-05-28T09:28:00Z", status:"pending",  suggestion:null,                                             files_touched:["src/payments/gateway.ts",".husky/pre-commit"]              },
  { session_id:"q2", developer:"Sara P",   tool:"Cursor",      branch:"wip-auth",          duration_min:45,  cost_usd:1.20, started_at:"2026-05-28T11:00:00Z", status:"pending",  suggestion:{ticket_id:"JIRA-155",title:"Auth SSO integration",confidence:48}, files_touched:["src/auth/token.ts","src/auth/session.ts"]          },
  { session_id:"q3", developer:"Raj K",    tool:"Claude Code", branch:"raj-working",       duration_min:120, cost_usd:2.10, started_at:"2026-05-27T14:00:00Z", status:"pending",  suggestion:{ticket_id:"JIRA-163",title:"Push notifications",confidence:41},   files_touched:["src/notifications/push.ts","lib/firebase.ts"]      },
  { session_id:"q4", developer:"Priya M",  tool:"Copilot",     branch:"undefined",         duration_min:32,  cost_usd:0.85, started_at:"2026-05-27T10:30:00Z", status:"pending",  suggestion:null,                                             files_touched:["src/components/SearchBar.tsx"]                             },
  { session_id:"q5", developer:"Vikram S", tool:"Cursor",      branch:"vk-test-branch",    duration_min:58,  cost_usd:1.64, started_at:"2026-05-26T16:00:00Z", status:"pending",  suggestion:{ticket_id:"JIRA-142",title:"Stripe gateway",confidence:39},        files_touched:["src/payments/stripe.ts","tests/payments.test.ts"]  },
  { session_id:"q6", developer:"Meera T",  tool:"Cursor",      branch:"explore-new-lib",   duration_min:24,  cost_usd:0.31, started_at:"2026-05-26T11:00:00Z", status:"pending",  suggestion:null,                                             files_touched:["package.json","src/utils/format.ts"]                      },
  { session_id:"q7", developer:"Dev A",    tool:"Copilot",     branch:"da-refactor",       duration_min:88,  cost_usd:2.40, started_at:"2026-05-25T14:00:00Z", status:"assigned", suggestion:{ticket_id:"JIRA-167",title:"Analytics tracking",confidence:72},    files_touched:["src/analytics/events.ts","src/tracking/index.ts"]  },
  { session_id:"q8", developer:"Sara P",   tool:"Cursor",      branch:"spike-redis",       duration_min:41,  cost_usd:0.96, started_at:"2026-05-25T09:00:00Z", status:"ignored",  suggestion:null,                                             files_touched:["src/cache/redis.ts"]                                      },
];

/* ─── Helpers ────────────────────────────────────────────── */
function Divider(){return <div style={{height:1,background:C.border}}/>;}

function Tag({children,color,bg}:any){
  return <span style={{padding:"2px 7px",borderRadius:4,background:bg,color,fontFamily:F.mono,fontSize:10,fontWeight:600,display:"inline-flex",alignItems:"center",gap:4}}>{children}</span>;
}

function timeAgo(iso:string):string{
  const diff=Date.now()-new Date(iso).getTime();
  const h=Math.floor(diff/3600000);
  const d=Math.floor(h/24);
  if(d>0)return `${d}d ago`;
  if(h>0)return `${h}h ago`;
  return "just now";
}

/* ─── Assign Modal ───────────────────────────────────────── */
function AssignModal({session,onAssign,onClose}:{
  session:QueueSession;
  onAssign:(ticketId:string)=>void;
  onClose:()=>void;
}){
  const [query,setQuery]=useState(session.suggestion?.ticket_id??"");
  const tickets=[
    {id:"JIRA-142",title:"Stripe payment gateway",sprint:"S42"},
    {id:"JIRA-151",title:"Data pipeline refactor",sprint:"S42"},
    {id:"JIRA-155",title:"Auth SSO integration",sprint:"S42"},
    {id:"JIRA-159",title:"Search & filter API",sprint:"S42"},
    {id:"JIRA-163",title:"Mobile push notifications",sprint:"S42"},
    {id:"JIRA-167",title:"Analytics event tracking",sprint:"S42"},
    {id:"JIRA-171",title:"User profile settings",sprint:"S42"},
  ];
  const filtered=tickets.filter(t=>
    t.id.toLowerCase().includes(query.toLowerCase())||
    t.title.toLowerCase().includes(query.toLowerCase())
  );

  return(
    <div style={{
      position:"fixed",inset:0,background:"rgba(0,0,0,0.7)",
      display:"flex",alignItems:"center",justifyContent:"center",zIndex:200,
    }} onClick={onClose}>
      <div onClick={e=>e.stopPropagation()} style={{
        background:C.card,border:`1px solid ${C.borderHi}`,
        borderRadius:12,width:460,overflow:"hidden",
        boxShadow:"0 24px 60px rgba(0,0,0,0.8)",
      }}>
        {/* Header */}
        <div style={{padding:"16px 20px 12px",borderBottom:`1px solid ${C.border}`,display:"flex",justifyContent:"space-between",alignItems:"flex-start"}}>
          <div>
            <div style={{fontFamily:F.ui,fontSize:14,fontWeight:600,color:C.text}}>Assign to ticket</div>
            <div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginTop:3}}>
              {session.developer} · {session.tool} · {session.duration_min}min · <span style={{color:C.warm}}>${session.cost_usd.toFixed(2)}</span>
            </div>
          </div>
          <button onClick={onClose} style={{background:"none",border:"none",cursor:"pointer",color:C.sub}}>
            <X size={16}/>
          </button>
        </div>

        {/* AI suggestion */}
        {session.suggestion&&(
          <div style={{padding:"10px 20px",background:C.accentBg,borderBottom:`1px solid ${C.border}`,display:"flex",alignItems:"center",gap:10}}>
            <Sparkles size={13} color={C.accent}/>
            <span style={{fontFamily:F.body,fontSize:12,color:C.text,flex:1}}>
              Suggested: <span style={{fontFamily:F.mono,color:C.accent}}>{session.suggestion.ticket_id}</span> — {session.suggestion.title}
            </span>
            <Tag color={C.amber} bg={C.amberBg}>{session.suggestion.confidence}% match</Tag>
            <button onClick={()=>onAssign(session.suggestion!.ticket_id)} style={{
              background:C.accentBg,border:`1px solid rgba(0,212,255,0.3)`,
              borderRadius:6,padding:"4px 10px",cursor:"pointer",
              fontFamily:F.body,fontSize:11,color:C.accent,
            }}>
              Confirm
            </button>
          </div>
        )}

        {/* Search */}
        <div style={{padding:"12px 20px",borderBottom:`1px solid ${C.border}`}}>
          <div style={{position:"relative"}}>
            <Search size={13} color={C.sub} style={{position:"absolute",left:10,top:"50%",transform:"translateY(-50%)"}}/>
            <input
              autoFocus
              value={query}
              onChange={e=>setQuery(e.target.value)}
              placeholder="Search tickets by ID or title..."
              style={{
                width:"100%",background:C.surface,border:`1px solid ${C.border}`,
                borderRadius:7,padding:"8px 12px 8px 32px",
                fontFamily:F.body,fontSize:12,color:C.text,outline:"none",
              }}
            />
          </div>
        </div>

        {/* Ticket list */}
        <div style={{maxHeight:240,overflowY:"auto"}}>
          {filtered.map((t,i)=>(
            <div key={i}>
              <div
                onClick={()=>onAssign(t.id)}
                style={{
                  display:"flex",justifyContent:"space-between",alignItems:"center",
                  padding:"10px 20px",cursor:"pointer",transition:"background .1s",
                }}
                onMouseEnter={e=>(e.currentTarget.style.background=C.hover)}
                onMouseLeave={e=>(e.currentTarget.style.background="transparent")}
              >
                <div>
                  <div style={{display:"flex",gap:10,alignItems:"center"}}>
                    <span style={{fontFamily:F.mono,fontSize:11,color:C.accent}}>{t.id}</span>
                    <span style={{fontFamily:F.body,fontSize:12,color:C.text}}>{t.title}</span>
                  </div>
                  <div style={{fontFamily:F.body,fontSize:10,color:C.sub,marginTop:2}}>{t.sprint} · active</div>
                </div>
                <ChevronRight size={13} color={C.sub}/>
              </div>
              {i<filtered.length-1&&<Divider/>}
            </div>
          ))}
          {filtered.length===0&&(
            <div style={{padding:"24px 20px",textAlign:"center",fontFamily:F.body,fontSize:12,color:C.sub}}>
              No matching tickets
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── Queue Row ──────────────────────────────────────────── */
function QueueRow({
  session, onAssign, onIgnore, onExploratory, isHov,
  onMouseEnter, onMouseLeave,
}:{
  session:QueueSession;
  onAssign:()=>void;
  onIgnore:()=>void;
  onExploratory:()=>void;
  isHov:boolean;
  onMouseEnter:()=>void;
  onMouseLeave:()=>void;
}){
  const statusCfg={
    pending:     { color:C.amber,  bg:C.amberBg,  label:"Pending"     },
    assigned:    { color:C.green,  bg:C.greenBg,  label:"Assigned"    },
    ignored:     { color:C.sub,    bg:C.muted,    label:"Ignored"     },
    exploratory: { color:C.purple, bg:"rgba(167,139,250,0.08)", label:"R&D" },
  }[session.status];

  const isPending=session.status==="pending";

  return(
    <div
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      style={{
        display:"grid",
        gridTemplateColumns:"1fr 90px 80px 70px 80px 80px 220px",
        gap:10,padding:"12px 18px",alignItems:"center",
        background:isHov&&isPending?C.hover:"transparent",
        transition:"background .1s",
        opacity:session.status!=="pending"?0.55:1,
      }}
    >
      {/* Session info */}
      <div>
        <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:3}}>
          <span style={{fontFamily:F.body,fontSize:12,color:C.text,fontWeight:500}}>{session.developer}</span>
          <span style={{fontFamily:F.mono,fontSize:10,color:C.sub}}>{session.tool}</span>
          <Tag color={statusCfg.color} bg={statusCfg.bg}>{statusCfg.label}</Tag>
        </div>
        <div style={{display:"flex",gap:10,alignItems:"center"}}>
          <span style={{fontFamily:F.mono,fontSize:10,color:C.sub,display:"flex",alignItems:"center",gap:3}}>
            <GitBranch size={9} color={C.sub}/> {session.branch}
          </span>
          <span style={{fontFamily:F.body,fontSize:10,color:C.sub}}>{timeAgo(session.started_at)}</span>
        </div>
      </div>

      {/* Duration */}
      <span style={{fontFamily:F.mono,fontSize:12,color:C.sub,display:"flex",alignItems:"center",gap:4}}>
        <Clock size={10} color={C.sub}/> {session.duration_min}min
      </span>

      {/* Cost */}
      <span style={{fontFamily:F.mono,fontSize:13,fontWeight:600,color:C.warm,display:"flex",alignItems:"center",gap:4}}>
        <DollarSign size={10} color={C.warm}/> ${session.cost_usd.toFixed(2)}
      </span>

      {/* Files */}
      <span style={{fontFamily:F.mono,fontSize:11,color:C.sub}}>
        {session.files_touched.length} file{session.files_touched.length!==1?"s":""}
      </span>

      {/* Suggestion */}
      <div>
        {session.suggestion?(
          <div>
            <div style={{fontFamily:F.mono,fontSize:11,color:C.amber}}>{session.suggestion.ticket_id}</div>
            <div style={{fontFamily:F.body,fontSize:9,color:C.sub,marginTop:1}}>{session.suggestion.confidence}% match</div>
          </div>
        ):(
          <span style={{fontFamily:F.body,fontSize:10,color:C.sub}}>—</span>
        )}
      </div>

      {/* Attribution confidence */}
      <div style={{display:"flex",alignItems:"center",gap:4}}>
        {session.suggestion&&(
          <div style={{flex:1,height:3,background:C.muted,borderRadius:2,overflow:"hidden"}}>
            <div style={{height:"100%",width:`${session.suggestion.confidence}%`,background:session.suggestion.confidence>=60?C.amber:C.red,borderRadius:2}}/>
          </div>
        )}
      </div>

      {/* Actions */}
      {isPending?(
        <div style={{display:"flex",gap:6}}>
          <button onClick={onAssign} style={{
            flex:1,background:C.accentBg,border:`1px solid rgba(0,212,255,0.25)`,
            borderRadius:6,padding:"5px 0",cursor:"pointer",
            fontFamily:F.body,fontSize:11,color:C.accent,
            display:"flex",alignItems:"center",justifyContent:"center",gap:4,
          }}>
            <TagIcon size={11}/> Assign
          </button>
          <button onClick={onIgnore} style={{
            background:"none",border:`1px solid ${C.border}`,
            borderRadius:6,padding:"5px 8px",cursor:"pointer",
            fontFamily:F.body,fontSize:11,color:C.sub,
            display:"flex",alignItems:"center",gap:3,
          }}>
            <X size={11}/> Ignore
          </button>
          <button onClick={onExploratory} style={{
            background:"none",border:`1px solid ${C.border}`,
            borderRadius:6,padding:"5px 8px",cursor:"pointer",
            fontFamily:F.body,fontSize:11,color:C.sub,
          }}
          title="Mark as R&D / exploratory">
            <MoreHorizontal size={13}/>
          </button>
        </div>
      ):(
        <div style={{fontFamily:F.body,fontSize:11,color:C.sub}}>
          {session.status==="assigned"&&"Assigned"}
          {session.status==="ignored"&&"Ignored"}
          {session.status==="exploratory"&&"R&D"}
        </div>
      )}
    </div>
  );
}

/* ─── Root ───────────────────────────────────────────────── */
export default function UnknownQueue(){
  const [sessions,setSessions]=useState<QueueSession[]>(MOCK_QUEUE);
  const [assignTarget,setAssignTarget]=useState<QueueSession|null>(null);
  const [hov,setHov]=useState<string|null>(null);
  const [filter,setFilter]=useState<"all"|"pending"|"resolved">("pending");
  const [search,setSearch]=useState("");

  const pendingCount=sessions.filter(s=>s.status==="pending").length;
  const pendingCost=sessions.filter(s=>s.status==="pending").reduce((a,s)=>a+s.cost_usd,0);

  const handleAssign=(sessionId:string,ticketId:string)=>{
    setSessions(prev=>prev.map(s=>s.session_id===sessionId?{...s,status:"assigned" as QueueStatus}:s));
    setAssignTarget(null);
  };
  const handleIgnore=(sessionId:string)=>{
    setSessions(prev=>prev.map(s=>s.session_id===sessionId?{...s,status:"ignored" as QueueStatus}:s));
  };
  const handleExploratory=(sessionId:string)=>{
    setSessions(prev=>prev.map(s=>s.session_id===sessionId?{...s,status:"exploratory" as QueueStatus}:s));
  };

  const filtered=sessions.filter(s=>{
    if(filter==="pending"&&s.status!=="pending")return false;
    if(filter==="resolved"&&s.status==="pending")return false;
    if(search&&!s.developer.toLowerCase().includes(search.toLowerCase())&&
       !s.branch.toLowerCase().includes(search.toLowerCase()))return false;
    return true;
  });

  return(
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=DM+Sans:opsz,wght@9..40,400;9..40,500&family=JetBrains+Mono:wght@400;500;600&display=swap');
        *{box-sizing:border-box;margin:0;padding:0}
        ::-webkit-scrollbar{width:4px}
        ::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:2px}
        input{font-family:'DM Sans',sans-serif}
        input::placeholder{color:#5A5A5A}
        button:focus{outline:none}
      `}</style>

      <div style={{minHeight:"100vh",background:C.bg,fontFamily:F.body,color:C.text}}>
        {/* Header */}
        <div style={{borderBottom:`1px solid ${C.border}`,padding:"18px 28px 16px",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
          <div>
            <div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginBottom:4}}>Management · Unknown Queue</div>
            <h1 style={{fontFamily:F.ui,fontSize:22,fontWeight:700,color:C.text,letterSpacing:"-0.02em"}}>Unknown Attribution Queue</h1>
            <div style={{fontFamily:F.body,fontSize:12,color:C.sub,marginTop:4}}>
              Sessions that couldn't be attributed automatically — assign to tickets to keep cost data accurate
            </div>
          </div>
        </div>

        <div style={{padding:"22px 28px",display:"flex",flexDirection:"column",gap:14}}>
          {/* Summary banner */}
          <div style={{
            background:pendingCount>0?C.amberBg:C.greenBg,
            border:`1px solid ${pendingCount>0?"rgba(255,184,0,0.2)":"rgba(0,230,118,0.2)"}`,
            borderRadius:10,padding:"14px 20px",
            display:"flex",alignItems:"center",gap:16,
          }}>
            {pendingCount>0
              ?<AlertTriangle size={18} color={C.amber}/>
              :<CheckCircle2 size={18} color={C.green}/>}
            <div style={{flex:1}}>
              <span style={{fontFamily:F.body,fontSize:14,color:C.text,fontWeight:500}}>
                {pendingCount>0
                  ?`${pendingCount} sessions need attribution`
                  :"All sessions attributed ✓"}
              </span>
              {pendingCount>0&&(
                <span style={{fontFamily:F.body,fontSize:13,color:C.sub,marginLeft:10}}>
                  representing <span style={{color:C.warm,fontFamily:F.mono,fontWeight:600}}>${pendingCost.toFixed(2)}</span> in unattributed AI spend
                </span>
              )}
            </div>
            {pendingCount>0&&(
              <div style={{fontFamily:F.body,fontSize:12,color:C.sub,display:"flex",gap:16}}>
                <span>{sessions.filter(s=>s.status==="assigned").length} assigned</span>
                <span>{sessions.filter(s=>s.status==="ignored").length} ignored</span>
                <span>{sessions.filter(s=>s.status==="exploratory").length} R&D</span>
              </div>
            )}
          </div>

          {/* Table */}
          <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:10,overflow:"hidden"}}>
            {/* Toolbar */}
            <div style={{
              padding:"12px 18px",display:"flex",gap:10,alignItems:"center",
              borderBottom:`1px solid ${C.border}`,
            }}>
              {/* Search */}
              <div style={{position:"relative",flex:1,maxWidth:280}}>
                <Search size={12} color={C.sub} style={{position:"absolute",left:10,top:"50%",transform:"translateY(-50%)"}}/>
                <input
                  value={search}
                  onChange={e=>setSearch(e.target.value)}
                  placeholder="Search developer or branch..."
                  style={{
                    width:"100%",background:C.surface,border:`1px solid ${C.border}`,
                    borderRadius:7,padding:"6px 12px 6px 30px",
                    fontSize:12,color:C.text,outline:"none",
                  }}
                />
              </div>
              {/* Filter tabs */}
              <div style={{display:"flex",gap:2,background:C.surface,borderRadius:7,padding:3,border:`1px solid ${C.border}`}}>
                {(["pending","all","resolved"] as const).map(f=>(
                  <button key={f} onClick={()=>setFilter(f)} style={{
                    background:filter===f?C.card:"none",
                    border:"none",cursor:"pointer",
                    fontFamily:F.body,fontSize:11,
                    color:filter===f?C.text:C.sub,
                    padding:"4px 12px",borderRadius:5,
                    textTransform:"capitalize",
                    transition:"all .1s",
                  }}>
                    {f}
                    {f==="pending"&&pendingCount>0&&(
                      <span style={{
                        marginLeft:5,background:C.amberBg,color:C.amber,
                        fontFamily:F.mono,fontSize:9,fontWeight:700,
                        padding:"1px 5px",borderRadius:10,
                      }}>{pendingCount}</span>
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Column headers */}
            <div style={{display:"grid",gridTemplateColumns:"1fr 90px 80px 70px 80px 80px 220px",gap:10,padding:"7px 18px"}}>
              {["Session","Duration","Cost","Files","Suggested","Confidence","Actions"].map(h=>(
                <span key={h} style={{fontFamily:F.body,fontSize:10,color:C.sub,textTransform:"uppercase",letterSpacing:"0.07em",fontWeight:600}}>{h}</span>
              ))}
            </div>
            <Divider/>

            {/* Rows */}
            {filtered.length===0?(
              <div style={{padding:"48px 0",textAlign:"center",fontFamily:F.body,fontSize:13,color:C.sub}}>
                {filter==="pending"?"No pending sessions — queue is clear ✓":"No sessions match this filter"}
              </div>
            ):(
              filtered.map((session,i)=>(
                <div key={session.session_id}>
                  <QueueRow
                    session={session}
                    onAssign={()=>setAssignTarget(session)}
                    onIgnore={()=>handleIgnore(session.session_id)}
                    onExploratory={()=>handleExploratory(session.session_id)}
                    isHov={hov===session.session_id}
                    onMouseEnter={()=>setHov(session.session_id)}
                    onMouseLeave={()=>setHov(null)}
                  />
                  {i<filtered.length-1&&<Divider/>}
                </div>
              ))
            )}

            {/* Footer */}
            {filtered.length>0&&(
              <>
                <Divider/>
                <div style={{padding:"10px 18px",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
                  <span style={{fontFamily:F.body,fontSize:11,color:C.sub}}>
                    Showing {filtered.length} of {sessions.length} sessions
                  </span>
                  <span style={{fontFamily:F.body,fontSize:11,color:C.sub}}>
                    Unattributed spend: <span style={{color:C.warm,fontFamily:F.mono,fontWeight:600}}>${pendingCost.toFixed(2)}</span>
                  </span>
                </div>
              </>
            )}
          </div>

          {/* Help callout */}
          <div style={{
            background:C.accentBg,border:`1px solid rgba(0,212,255,0.12)`,
            borderRadius:10,padding:"14px 18px",
            display:"flex",gap:12,alignItems:"flex-start",
          }}>
            <Sparkles size={15} color={C.accent} style={{flexShrink:0,marginTop:2}}/>
            <div>
              <div style={{fontFamily:F.body,fontSize:13,color:C.text,fontWeight:500,marginBottom:4}}>
                Why do sessions end up here?
              </div>
              <div style={{fontFamily:F.body,fontSize:12,color:C.sub,lineHeight:1.6}}>
                Sessions without a recognisable ticket ID in the branch name are held here.
                Encourage developers to name branches like <span style={{fontFamily:F.mono,color:C.accent}}>feature/JIRA-142-description</span> to
                reduce this queue. Manual corrections are saved and used to improve future attribution.
                Sessions marked as <strong style={{color:C.text}}>R&D / exploratory</strong> are tracked separately and excluded from ticket KPIs.
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Assign modal */}
      {assignTarget&&(
        <AssignModal
          session={assignTarget}
          onAssign={(ticketId)=>handleAssign(assignTarget.session_id,ticketId)}
          onClose={()=>setAssignTarget(null)}
        />
      )}
    </>
  );
}
