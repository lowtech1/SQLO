import com.alibaba.fastjson.JSONArray;
import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;
import main.Rewriter;
import main.Utils;
import org.apache.calcite.plan.RelOptRule;
import org.apache.calcite.plan.hep.HepMatchOrder;
import org.apache.calcite.plan.hep.HepPlanner;
import org.apache.calcite.plan.hep.HepProgramBuilder;
import org.apache.calcite.rel.RelNode;
import org.apache.calcite.rel.rel2sql.RelToSqlConverter;
import org.apache.calcite.rel.rules.CoreRules;
import org.apache.calcite.sql.dialect.PostgresqlSqlDialect;

import java.lang.reflect.Type;
import java.util.List;
import java.util.Scanner;

public class get_logical_plan {
    public static void main(String[] args) throws Exception{
        String path = System.getProperty("user.dir");
        // Sua loi: split "/" khong hoat dong tren Windows (path chua "\")
        String normalized = path.replace("\\", "/");
        String[] levels = normalized.split("/");
        // Loai bo 1 cap thu muc cuoi (src) -> len 2 cap de den project root
        StringBuilder modifiedPath = new StringBuilder();
        for(int i = 0; i < levels.length - 1; i++) {
            modifiedPath.append(levels[i]);
            if(i < levels.length - 2) {
                modifiedPath.append("/");
            }
        }
        String newpath = modifiedPath.toString();
        if(newpath.isEmpty()) newpath = path;
        Scanner scanner = new Scanner(System.in);
        String inputs = scanner.nextLine();
        Gson gson = new Gson();
        Type type = new TypeToken<List<Object>>(){}.getType();
        List<Object> inputList = gson.fromJson(inputs, type);
        String db_id = (String) inputList.get(0);
        String testSql = (String) inputList.get(1);
        testSql = testSql.replace(";", "");
        JSONArray schemaJson = Utils.readJsonFile(newpath+"/data/data_llmr2/schemas/" + db_id + ".json");
        Rewriter rewriter = new Rewriter(schemaJson);
        RelNode testRelNode = rewriter.SQL2RA(testSql);
        System.out.println(testRelNode.explain());

    }
}
