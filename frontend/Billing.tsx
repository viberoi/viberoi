/**
 * S-10 Settings — Billing
 * Plan, active devices, usage history, payment method.
 * Access: Org Admin only.
 */

import { useState } from "react";
import { CreditCard, Download, ChevronDown, Zap, TrendingUp } from "lucide-react";

const C={bg:"#080808",card:"#101010",surface:"#181818",hover:"#1E1E1E",accent:"#00D4FF",accentBg:"rgba(0,212,255,0.08)",warm:"#FFB547",warmBg:"rgba(255,181,71,0.08)",green:"#00E676",greenBg:"rgba(0,230,118,0.08)",red:"#FF4545",redBg:"rgba(255,69,69,0.08)",amber:"#FFB800",amberBg:"rgba(255,184,0,0.08)",purple:"#A78BFA",text:"#F0F0F0",sub:"#5A5A5A",muted:"#2E2E2E",border:"rgba(255,255,255,0.07)",borderHi:"rgba(255,255,255,0.14)"} as const;
const F={ui:"'Outfit',sans-serif",body:"'DM Sans',sans-serif",mono:"'JetBrains Mono',monospace"};

const BILLING = {
  plan:"starter",
  trial:{active:false,days_remaining:0},
  devices:{active:10,inactive:2,limit:15,billing_month:"June 2026"},
  current_bill:{amount:100,period:"Jun 2026",next_billing:"Jul 1, 2026",per_device:10},
  payment:{last4:"4242",brand:"Visa",expires:"12/27"},
  history:[
    {month:"May 2026",devices:9,amount:90,status:"paid"},
    {month:"Apr 2026",devices:8,amount:80,status:"paid"},
    {month:"Mar 2026",devices:7,amount:70,status:"paid"},
    {month:"Feb 2026",devices:6,amount:60,status:"paid"},
    {month:"Jan 2026",devices:5,amount:50,status:"paid"},
    {month:"Dec 2025",devices:5,amount:50,status:"paid"},
  ],
};

const PLANS=[
  {name:"Starter",devs:"1–15 devices",price:"$10",per:"device/month",current:true,features:["All KPI dashboards","Unlimited manager seats","Slack + Email alerts","Monthly billing"]},
  {name:"Growth",devs:"16–50 devices",price:"$8",per:"device/month",current:false,features:["Everything in Starter","API access","All notification channels","Annual discount (2mo free)"]},
  {name:"Scale",devs:"51–150 devices",price:"$6",per:"device/month",current:false,features:["Everything in Growth","Priority support","Custom reports","Quarterly invoicing"]},
];

function Divider(){return <div style={{height:1,background:C.border}}/>;}

export default function Billing(){
  const b=BILLING;
  const devicePct=(b.devices.active/b.devices.limit)*100;
  return(
    <>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=DM+Sans:opsz,wght@9..40,400;9..40,500&family=JetBrains+Mono:wght@400;500;600&display=swap');*{box-sizing:border-box;margin:0;padding:0}::-webkit-scrollbar{width:4px}::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:2px}`}</style>
      <div style={{minHeight:"100vh",background:C.bg,fontFamily:F.body,color:C.text}}>
        <div style={{borderBottom:`1px solid ${C.border}`,padding:"18px 28px 16px"}}>
          <div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginBottom:4}}>Settings · Billing</div>
          <h1 style={{fontFamily:F.ui,fontSize:22,fontWeight:700,color:C.text,letterSpacing:"-0.02em"}}>Billing & Subscription</h1>
          <div style={{fontFamily:F.body,fontSize:12,color:C.sub,marginTop:4}}>Manage your plan, active devices, and payment method</div>
        </div>
        <div style={{padding:"22px 28px",display:"flex",flexDirection:"column",gap:14}}>

          {/* Current plan + usage */}
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:14}}>
            <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:10,padding:"18px"}}>
              <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:16}}>
                <div>
                  <div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginBottom:4,textTransform:"uppercase",letterSpacing:"0.06em"}}>Current plan</div>
                  <div style={{fontFamily:F.ui,fontSize:22,fontWeight:700,color:C.accent}}>Starter</div>
                  <div style={{fontFamily:F.body,fontSize:12,color:C.sub,marginTop:3}}>1–15 active devices · $10/device/month</div>
                </div>
                <div style={{background:C.accentBg,border:`1px solid rgba(0,212,255,0.2)`,borderRadius:8,padding:"8px 14px",textAlign:"center"}}>
                  <div style={{fontFamily:F.mono,fontSize:20,fontWeight:600,color:C.warm}}>${b.current_bill.amount}</div>
                  <div style={{fontFamily:F.body,fontSize:10,color:C.sub,marginTop:2}}>this month</div>
                </div>
              </div>
              <div style={{marginBottom:12}}>
                <div style={{display:"flex",justifyContent:"space-between",marginBottom:6}}>
                  <span style={{fontFamily:F.body,fontSize:12,color:C.text}}>Active devices ({b.billing_month})</span>
                  <span style={{fontFamily:F.mono,fontSize:12,fontWeight:600,color:C.accent}}>{b.devices.active} / {b.devices.limit}</span>
                </div>
                <div style={{height:6,background:C.muted,borderRadius:3,overflow:"hidden"}}>
                  <div style={{height:"100%",width:`${devicePct}%`,background:devicePct>80?C.amber:C.accent,borderRadius:3}}/>
                </div>
                <div style={{fontFamily:F.body,fontSize:10,color:C.sub,marginTop:4}}>{b.devices.inactive} inactive devices not billed this month</div>
              </div>
              <Divider/>
              <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginTop:12}}>
                <div>
                  <div style={{fontFamily:F.body,fontSize:11,color:C.sub}}>Next billing</div>
                  <div style={{fontFamily:F.mono,fontSize:12,color:C.text}}>{b.current_bill.next_billing}</div>
                </div>
                <div style={{display:"flex",alignItems:"center",gap:8}}>
                  <CreditCard size={13} color={C.sub}/>
                  <span style={{fontFamily:F.mono,fontSize:12,color:C.text}}>{b.payment.brand} ···{b.payment.last4}</span>
                  <button style={{background:"none",border:`1px solid ${C.border}`,borderRadius:5,padding:"3px 8px",cursor:"pointer",fontFamily:F.body,fontSize:10,color:C.sub}}>Update</button>
                </div>
              </div>
            </div>

            {/* Plan comparison */}
            <div style={{display:"flex",flexDirection:"column",gap:8}}>
              {PLANS.map((plan,i)=>(
                <div key={i} style={{background:plan.current?C.accentBg:C.card,border:`1px solid ${plan.current?"rgba(0,212,255,0.25)":C.border}`,borderRadius:9,padding:"12px 14px",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
                  <div>
                    <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:3}}>
                      <span style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:plan.current?C.accent:C.text}}>{plan.name}</span>
                      {plan.current&&<span style={{fontFamily:F.mono,fontSize:9,fontWeight:600,color:C.accent,background:"rgba(0,212,255,0.15)",padding:"1px 6px",borderRadius:10}}>CURRENT</span>}
                    </div>
                    <span style={{fontFamily:F.body,fontSize:11,color:C.sub}}>{plan.devs}</span>
                  </div>
                  <div style={{textAlign:"right"}}>
                    <div style={{fontFamily:F.mono,fontSize:16,fontWeight:600,color:plan.current?C.accent:C.text}}>{plan.price}</div>
                    <div style={{fontFamily:F.body,fontSize:10,color:C.sub}}>{plan.per}</div>
                    {!plan.current&&<button style={{marginTop:6,background:"none",border:`1px solid ${C.border}`,borderRadius:5,padding:"3px 9px",cursor:"pointer",fontFamily:F.body,fontSize:10,color:C.sub}}>Upgrade</button>}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Usage history */}
          <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:10,overflow:"hidden"}}>
            <div style={{padding:"14px 18px 10px",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
              <div><div style={{fontFamily:F.ui,fontSize:13,fontWeight:600,color:C.text}}>Usage History</div><div style={{fontFamily:F.body,fontSize:11,color:C.sub,marginTop:2}}>Last 6 months · active device count and billing</div></div>
              <button style={{background:"none",border:`1px solid ${C.border}`,borderRadius:6,padding:"5px 10px",cursor:"pointer",fontFamily:F.body,fontSize:11,color:C.sub,display:"flex",alignItems:"center",gap:5}}><Download size={11}/> Export</button>
            </div>
            <Divider/>
            <div style={{display:"grid",gridTemplateColumns:"1fr 100px 100px 80px",gap:10,padding:"6px 18px"}}>
              {["Month","Active devices","Amount","Status"].map(h=>(<span key={h} style={{fontFamily:F.body,fontSize:10,color:C.sub,textTransform:"uppercase",letterSpacing:"0.06em",fontWeight:600}}>{h}</span>))}
            </div>
            <Divider/>
            {b.history.map((row,i)=>(
              <div key={i}>
                <div style={{display:"grid",gridTemplateColumns:"1fr 100px 100px 80px",gap:10,padding:"10px 18px",alignItems:"center"}}>
                  <span style={{fontFamily:F.body,fontSize:12,color:C.text}}>{row.month}</span>
                  <span style={{fontFamily:F.mono,fontSize:12,color:C.sub}}>{row.devices} devices</span>
                  <span style={{fontFamily:F.mono,fontSize:12,fontWeight:600,color:C.warm}}>${row.amount}</span>
                  <span style={{fontFamily:F.mono,fontSize:10,color:C.green}}>✓ {row.status}</span>
                </div>
                {i<b.history.length-1&&<Divider/>}
              </div>
            ))}
          </div>

          {/* Active device definition */}
          <div style={{background:C.accentBg,border:`1px solid rgba(0,212,255,0.12)`,borderRadius:9,padding:"12px 16px",display:"flex",gap:10,alignItems:"flex-start"}}>
            <Zap size={13} color={C.accent} style={{flexShrink:0,marginTop:2}}/>
            <div style={{fontFamily:F.body,fontSize:12,color:C.sub,lineHeight:1.6}}>
              <strong style={{color:C.text}}>Active device definition:</strong> A device is billed as active when the agent is installed AND captures at least 5 sessions in the billing month. Developers on leave or machines that are off are not charged. You only pay for actual AI usage.
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
