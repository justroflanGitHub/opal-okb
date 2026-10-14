
void FUN_2000_6191(undefined2 param_1,undefined2 *param_2,int *param_3,int *param_4,
                  undefined2 param_5,undefined2 param_6)

{
  uint *puVar1;
  uint uVar2;
  int iVar3;
  undefined2 uVar4;
  undefined2 uVar5;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  undefined4 uVar6;
  undefined1 local_6 [2];
  undefined2 local_4;
  
  iVar3 = *(int *)0x1944;
  uVar5 = *(undefined2 *)0x1946;
  uVar4 = ((undefined2 *)param_2)[1];
  *(undefined2 *)0x557e = *param_2;
  *(undefined2 *)0x5580 = uVar4;
  uVar4 = FUN_3000_97a9(0x1000);
  *(undefined2 *)0x558a = uVar4;
  if (*(int *)0xa == 0) {
    uVar6 = func_0x0003918b(0x2e73);
    *(undefined2 *)0x5576 = (int)uVar6;
    *(undefined2 *)0x5578 = (int)((ulong)uVar6 >> 0x10);
    uVar6 = func_0x0003917d(0x2e73,*(undefined2 *)0x0,*(undefined2 *)0x2);
    *(undefined2 *)0x5572 = (int)uVar6;
    *(undefined2 *)0x5574 = (int)((ulong)uVar6 >> 0x10);
  }
  else if ((-1 < *(int *)0x5580) && ((0 < *(int *)0x5580 || (0x10 < *(uint *)0x557e)))) {
    puVar1 = (uint *)0x557e;
    uVar2 = *puVar1;
    *puVar1 = *puVar1 - 0x10;
    *(int *)0x5580 = *(int *)0x5580 - (uint)(uVar2 < 0x10);
  }
  FUN_3000_97af(0x2e73,1,1,*(undefined2 *)0x6,*(undefined2 *)0x4);
  if ((*param_4 != 0 || ((int *)param_4)[1] != 0) && (*param_3 != 0 || ((int *)param_3)[1] != 0)) {
    func_0x00039bca(0x2e73,*param_3,*param_4,0x557a);
    uVar4 = FUN_3000_9798(0x2e73,*(undefined2 *)0x557e);
    *(undefined2 *)0x558c = uVar4;
    local_4 = *(undefined2 *)(iVar3 + 2);
    *(int *)0x1944 = (int)local_6;
    *(undefined2 *)0x1946 = unaff_SS;
    FUN_3000_9bfc(0x2e73,param_5,param_6);
  }
  uVar5 = FUN_3000_9798(0x2e73,*(undefined2 *)0x4);
  *(undefined2 *)0x558c = uVar5;
  FUN_3000_35a2(0x2e73,0x5588);
  func_0x00039bca(0x2e73,1,0x43,0x557a);
  func_0x0002f5ce(0x2e73,0x4e8,*(undefined2 *)0x5582);
  return;
}

