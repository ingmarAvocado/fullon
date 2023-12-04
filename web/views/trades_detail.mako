<%
import arrow
%>
<div class="container">
    <p></p>
    <h6>Bot Details</h6>
        <table id="fullon" class="display compact  table-striped table-bordered" style="width:100%"> 
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Exchange</th>
                    <th>Symbol</th>
                    <th>Lev</th>
                    <th>Max Entry</th>
                    <th>Live</th>
                    <th>market</th>
                    <th>ROI</th>
                    <th>Fees</th>
                    <th>Since</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>${bot_view.name}</td>
                    <td>${bot_view.ex_name}</td>
                    <td>${bot_view.symbol}</td>
                    <td>${bot_view.leverage}</td>
                    <td>${bot_view.pct}%</td>
                    <td>${bot.live}</td>
                    <td>${bot.market}</td>
                    <td>${totals.roi}</td>
                    <td>${totals.fee}</td>
                    <td>${bot.timestamp}</td>
                </tr>               
            </tbody>
        </table>
    
    
  
    <p></p>
    <h6>Bot History: last 100 trades</h6>
        <table id="fullon" class="display table-striped table-bordered" style="width:100%"> 
            <thead>
                <tr>
                    <th>Side</th>
                    <th>Quantity</th>
                    <th>Price</th>
                    <th>Cost</th>
                    <th>Fee</th>
                    <th>Roi</th>
                    <th>%</th>
                    <th>Date</th>
                </tr>
            </thead>
            <tbody>
                % for t in trades:
                <tr>
                    <td>${t.side}</td>
                     <%
                        if t.quantity > 10:
                            t.quantity=round(t.quantity,2)
                        elif t.cost >= 1:
                            t.quantity=round(t.quantity,4)
                        else:
                            t.quantity=round(t.quantity,8)
                    
                    %>
                    <td>${t.quantity}</td>
                    <%
                        if t.price > 10:
                            t.price=round(t.price,2)
                        elif t.cost >= 1:
                            t.price=round(t.price,4)
                        else:
                            t.price=round(t.price,8)
                    
                    %>                    
                    <td>${t.price}</td>  
                    <%
                        if t.cost > 10:
                            t.cost=round(t.cost,2)
                        elif t.cost >= 1:
                            t.cost=round(t.cost,4)
                        else:
                            t.cost=round(t.cost,8)
                    
                    %>
                                     
                    <td>${t.cost}</td>
                    
                    <%
                        tmp_fee=t.fee
                        if t.fee < 0:
                            tmp_fee = t.fee *-1
                        if tmp_fee  < 1:
                            t.fee=f'{t.fee:.8f}'
                        elif tmp_fee >= 1 and tmp_fee < 10:
                            t.fee=f'{t.fee:.4f}'
                        else:
                            t.fee=f'{t.fee:.2f}'
                    %>
                    
                    <td>${t.fee}</td>
                    
                    <%
                        tmp_roi = t.roi
                        if t.roi == None:
                            t.roi = 0
                            t.roi_usd = 0
                            t.roi_pct = 0
                        else:
                            if t.roi < 0:
                                tmp_roi = t.roi * -1
                            if tmp_roi  < 1:
                                t.roi =  f'{t.roi:.8f}'
                            elif tmp_roi >= 1 and tmp_roi < 10:
                                t.roi = f'{t.roi:.4f}'
                            else:
                                t.roi = f'{t.roi:.2f}'
                        
                    %>
                    <td>${t.roi}</td>
                    <%
                        flag="secondary"
                        if t.roi_pct < 0:
                            flag="danger"
                        elif t.roi_pct > 0:
                            flag="success"
                    %>
                    <td><p class="text-${flag}">${t.roi_pct}%</p></td>
                    <%
                        ts = arrow.get(t.timestamp)
                    %>
                    <td>${ts.format('YYYY-MM-DD HH:mm:ss')}</td>
                </tr>
                % endfor
            </tbody>
        </table>


        
    
</div>
